# vim: expandtab:ts=4:sw=4
from __future__ import absolute_import
import numpy as np
from . import kalman_filter
from . import linear_assignment
from . import iou_matching
from .track import Track


class Tracker:
    """
    This is the multi-target tracker.

    Parameters
    ----------
    metric : nn_matching.NearestNeighborDistanceMetric
        A distance metric for measurement-to-track association.
    max_age : int
        Maximum number of missed misses before a track is deleted.
    n_init : int
        Number of consecutive detections before the track is confirmed. The
        track state is set to `Deleted` if a miss occurs within the first
        `n_init` frames.

    Attributes
    ----------
    metric : nn_matching.NearestNeighborDistanceMetric
        The distance metric used for measurement to track association.
    max_age : int
        Maximum number of missed misses before a track is deleted.
    n_init : int
        Number of frames that a track remains in initialization phase.
    kf : kalman_filter.KalmanFilter
        A Kalman filter to filter target trajectories in image space.
    tracks : List[Track]
        The list of active tracks at the current time step.

    """

    def __init__(self, metric, max_iou_distance=0.7, max_age=70, n_init=2, n_start=0):
        self.metric = metric
        self.max_iou_distance = max_iou_distance
        self.max_age = max_age
        self.n_init = n_init

        self.kf = kalman_filter.KalmanFilter()    # 卡门滤波
        self.tracks = []
        self._next_id = n_start + 1

    def predict(self):
        """Propagate track state distributions one time step forward.

        This function should be called once every time step, before `update`.
        """
        for track in self.tracks:
            track.predict(self.kf)

    def update(self, detections):
        """Perform measurement update and track management.

        Parameters
        ----------
        detections : List[deep_sort.detection.Detection]
            A list of detections at the current time step.

        """
        # Run matching cascade.先基于 代价矩阵 匹配，再基于 iou 匹配
        # 代价矩阵：通过 卡门滤波预测到的框tracks 和 实际检出的框detections 计算得出
        matches, unmatched_tracks, unmatched_detections = \
            self._match(detections)

        # Update track set.
        for track_idx, detection_idx in matches:
            self.tracks[track_idx].update(
                self.kf, detections[detection_idx])
        for track_idx in unmatched_tracks:    # 未匹配的tracks认为丢失
            self.tracks[track_idx].mark_missed()
        for detection_idx in unmatched_detections:    # 未匹配的detections认为是新目标
            self._initiate_track(detections[detection_idx])
        self.tracks = [t for t in self.tracks if not t.is_deleted()]

        # Update distance metric.
        active_targets = [t.track_id for t in self.tracks if t.is_confirmed()]
        features, targets = [], []
        for track in self.tracks:
            if not track.is_confirmed():
                continue
            features += track.features
            targets += [track.track_id for _ in track.features]
            track.features = []
        self.metric.partial_fit(
            np.asarray(features), np.asarray(targets), active_targets)

    '''
        用卡门滤波与检测出的detection进行匹配，没匹配到的认为目标丢失
    '''
    def _match(self, detections):

        # 基于外观信息和马氏距离，计算卡门滤波预测的tracks和当前时刻检测到的detections的代价矩阵
        def gated_metric(tracks, dets, track_indices, detection_indices):
            features = np.array([dets[i].feature for i in detection_indices])    # 检测到的
            targets = np.array([tracks[i].track_id for i in track_indices])      # 卡门滤波预测到的

            # 基于外观信息，计算代价矩阵（内容：tracks和detections的features的余弦距离）
            cost_matrix = self.metric.distance(features, targets)    # 分别计算features（检测到的特征）和targets（卡门滤波预测到的track_id）的余弦距离

            # 基于马氏距离，过滤掉代价矩阵中的不合适的项（将其设置为一个较大的值）
            cost_matrix = linear_assignment.gate_cost_matrix(
                self.kf, cost_matrix, tracks, dets, track_indices,
                detection_indices)

            return cost_matrix    # 返回代价矩阵

        # Split track set into confirmed and unconfirmed tracks.，分别处理已确认的和未确认的
        confirmed_tracks = [
            i for i, t in enumerate(self.tracks) if t.is_confirmed()]
        unconfirmed_tracks = [
            i for i, t in enumerate(self.tracks) if not t.is_confirmed()]

        # Associate confirmed tracks using appearance features.，对已确认的tracks进行级联匹配
        # 1.已确认的，基于 代价矩阵 匹配
        matches_a, unmatched_tracks_a, unmatched_detections = \
            linear_assignment.matching_cascade(
                gated_metric, self.metric.matching_threshold, self.max_age,
                self.tracks, detections, confirmed_tracks)    # 通过matching_cascade()间接调用min_cost_matching()，里面有基于匈牙利算法进行匹配

        # Associate remaining tracks together with unconfirmed tracks using IOU.
        # 2.未确认的，基于 iou 匹配
        # 对级联匹配未匹配上的tracks、未确认的tracks中time_since_update为1的tracks进行IOU匹配
        iou_track_candidates = unconfirmed_tracks + [
            k for k in unmatched_tracks_a if
            self.tracks[k].time_since_update == 1]
        unmatched_tracks_a = [
            k for k in unmatched_tracks_a if
            self.tracks[k].time_since_update != 1]
        matches_b, unmatched_tracks_b, unmatched_detections = \
            linear_assignment.min_cost_matching(
                iou_matching.iou_cost, self.max_iou_distance, self.tracks,
                detections, iou_track_candidates, unmatched_detections)    # 直接调min_cost_matching()，里面有基于匈牙利算法进行匹配

        # 整合所有匹配的和未匹配的
        matches = matches_a + matches_b
        unmatched_tracks = list(set(unmatched_tracks_a + unmatched_tracks_b))
        return matches, unmatched_tracks, unmatched_detections

    def _initiate_track(self, detection):
        mean, covariance = self.kf.initiate(detection.to_xyah())
        self.tracks.append(Track(
            mean, covariance, self._next_id, self.n_init, self.max_age,
            detection.classes,                           # 加上类别
            detection.feature, detection.confidence))    # 加上置信度
        self._next_id += 1
