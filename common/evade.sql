/*
 Navicat Premium Data Transfer

 Source Server         : localhost_mysql
 Source Server Type    : MySQL
 Source Server Version : 80012
 Source Host           : localhost:3306
 Source Schema         : evade

 Target Server Type    : MySQL
 Target Server Version : 80012
 File Encoding         : 65001

 Date: 22/07/2020 09:15:31
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for cap_location
-- ----------------------------
DROP TABLE IF EXISTS `cap_location`;
CREATE TABLE `cap_location`  (
  `ip` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '摄像头ip',
  `gate_num` varchar(2) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '闸机编号',
  `direction` varchar(2) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '闸机方向：0出站，1进站，2双向',
  `default_direct` varchar(2) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '默认闸机方向，针对双向闸机，跟谁在一起就默认跟谁方向一样',
  `entrance` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '出入口：AE、D或B',
  `entrance_direct` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '出入口的进出站：0出站，1进站',
  `entrance_gate_num` varchar(2) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '画面中闸机编号与真实闸机编号的绑定',
  `displacement` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '位移方向：up（画面中向上走），down（画面中向下走）',
  `passway_area` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '画面中通道检测区域，左上右下',
  `gate_area` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '画面中闸机门检测区域，左上右下',
  `gate_light_area` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '画面中闸机灯检测区域，左上右下',
  `current_image_shape` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '当前画面尺寸：w*h',
  `create_time` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '创建时间',
  `stop_time` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '停用时间',
  `is_enabled` varchar(2) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '是否启用：y已启用；n已停用'
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of cap_location
-- ----------------------------
INSERT INTO `cap_location` VALUES ('10.6.8.181', '0', '2', '0', 'D', '0', '0', 'down', '0_0_155_360', '0_176_118_199', '0_0_0_0', '640x360', '2020-07-16 14:19:02', NULL, 'n');
INSERT INTO `cap_location` VALUES ('10.6.8.181', '1', '0', '0', 'D', '0', '1', 'down', '235_0_420_360', '249_128_408_183', '176_161_240_199', '640x360', '2020-07-16 14:20:26', NULL, 'n');
INSERT INTO `cap_location` VALUES ('10.6.8.181', '2', '0', '0', 'D', '0', '2', 'down', '480_0_604_360', '488_161_582_202', '421_150_487_189', '640x360', '2020-07-16 14:21:36', NULL, 'n');
INSERT INTO `cap_location` VALUES ('10.6.8.222', '0', '1', '1', 'AE', '1', '0', 'up', '114_0_282_480', '133_176_271_230', '271_187_344_234', '640x480', '2020-07-16 14:30:16', NULL, 'n');
INSERT INTO `cap_location` VALUES ('10.6.8.222', '1', '1', '1', 'AE', '1', '1', 'up', '339_0_504_360', '349_218_489_268', '504_188_558_232', '640x480', '2020-07-16 14:31:28', NULL, 'n');
INSERT INTO `cap_location` VALUES ('10.6.8.222', '2', '1', '1', 'AE', '1', '2', 'up', '550_0_640_480', '558_174_627_224', '0_0_0_0', '640x480', '2020-07-16 14:32:26', NULL, 'n');
INSERT INTO `cap_location` VALUES ('10.6.8.181', '0', '2', '0', 'D', '0', '0', 'down', '0_0_470_1080', '3_531_353_589', '0_0_0_0', '1920x1080', '2020-07-21_18:19:35', NULL, 'y');
INSERT INTO `cap_location` VALUES ('10.6.8.181', '1', '0', '0', 'D', '0', '1', 'down', '730_0_1277_1080', '755_413_1213_525', '531_487_709_595', '1920x1080', '2020-07-21_18:23:20', NULL, 'y');
INSERT INTO `cap_location` VALUES ('10.6.8.181', '2', '0', '0', 'D', '0', '2', 'down', '1379_0_1823_1080', '1463_487_1737_595', '1269_455_1449_561', '1920x1080', '2020-07-21_18:26:42', NULL, 'y');
INSERT INTO `cap_location` VALUES ('10.6.8.222', '0', '1', '1', 'AE', '1', '0', 'up', '343_0_859_1080', '413_411_809_537', '825_447_1023_559', '1920x1080', '2020-07-21_18:30:25', NULL, 'y');
INSERT INTO `cap_location` VALUES ('10.6.8.222', '1', '1', '1', 'AE', '1', '1', 'up', '1017_0_1539_1080', '1051_499_1469_613', '1531_437_1681_539', '1920x1080', '2020-07-21_18:33:18', NULL, 'y');
INSERT INTO `cap_location` VALUES ('10.6.8.222', '2', '1', '1', 'AE', '1', '2', 'up', '1571_0_1920_1080', '1675_399_1893_503', '0_0_0_0', '1920x1080', '2020-07-21_18:35:24', NULL, 'y');

-- ----------------------------
-- Table structure for details_10_6_8_181
-- ----------------------------
DROP TABLE IF EXISTS `details_10_6_8_181`;
CREATE TABLE `details_10_6_8_181`  (
  `curr_time` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '当前时刻，精确到s',
  `savefile` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '保存文件路径',
  `pass_status` varchar(2) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '通过状态：0正常通过，1涉嫌逃票',
  `read_time` float(10, 5) NULL DEFAULT NULL COMMENT '读取耗时',
  `detect_time` float(10, 5) NULL DEFAULT NULL COMMENT '检测耗时',
  `predicted_class` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '检测类别',
  `score` float(10, 5) NULL DEFAULT NULL COMMENT '得分值',
  `box` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '人头框，左上右下',
  `person_id` int(10) NULL DEFAULT NULL COMMENT '人物id',
  `trackState` int(2) NULL DEFAULT NULL COMMENT '确认状态：1未确认，2已确认',
  `ip` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '摄像机ip',
  `gate_num` varchar(2) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '闸机编号',
  `gate_status` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '闸机门状态',
  `gate_light_status` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '闸机灯状态',
  `direction` varchar(2) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '方向：0出站，1进站'
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of details_10_6_8_181
-- ----------------------------

INSERT INTO `details_10_6_8_181` VALUES ('2020-07-23_18:16:05', 'D:/monitor_images/10.6.8.181/normal_images/10.6.8.181_20200723_181605.jpg', '0', 0.03989, 3.76919, 'head', 0.40521, '0_893_129_1097', 1, 1, '10.6.8.181', '0', 'closed', 'NoLight', '0');
INSERT INTO `details_10_6_8_181` VALUES ('2020-07-23_18:16:08', 'D:/monitor_images/10.6.8.181/normal_images/10.6.8.181_20200723_181608.jpg', '0', 0.00895, 0.07679, 'head', 0.32484, '11_919_116_1084', 1, 1, '10.6.8.181', '0', 'closed', 'NoLight', '0');
INSERT INTO `details_10_6_8_181` VALUES ('2020-07-23_18:16:15', 'D:/monitor_images/10.6.8.181/normal_images/10.6.8.181_20200723_181615.jpg', '0', 0.00701, 0.08375, 'head', 0.43349, '1652_7_1874_154', 2, 1, '10.6.8.181', '2', 'open', 'greenLight', '0');
INSERT INTO `details_10_6_8_181` VALUES ('2020-07-23_18:16:15', 'D:/monitor_images/10.6.8.181/normal_images/10.6.8.181_20200723_181615.jpg', '0', 0.00898, 0.08827, 'head', 0.71278, '1647_5_1878_158', 2, 1, '10.6.8.181', '2', 'open', 'greenLight', '0');
INSERT INTO `details_10_6_8_181` VALUES ('2020-07-23_18:16:15', 'D:/monitor_images/10.6.8.181/normal_images/10.6.8.181_20200723_181615.jpg', '0', 0.00798, 0.08674, 'head', 0.88786, '1636_1_1891_170', 2, 2, '10.6.8.181', '2', 'open', 'greenLight', '0');

SET FOREIGN_KEY_CHECKS = 1;

-- ----------------------------
-- Table structure for evade_details_10_6_8_181
-- ----------------------------
DROP TABLE IF EXISTS `evade_details`;
CREATE TABLE `evade_details`  (
  `uuid` int(50) NOT NULL AUTO_INCREMENT COMMENT '自增id',
  `curr_time` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '当前时刻，精确到s',
  `savefile` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '保存文件路径',
  `pass_status` varchar(2) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '通过状态：0正常通过，1涉嫌逃票',
  `read_time` float(10, 5) NULL DEFAULT NULL COMMENT '读取耗时',
  `detect_time` float(10, 5) NULL DEFAULT NULL COMMENT '检测耗时',
  `predicted_class` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '检测类别',
  `score` float(10, 5) NULL DEFAULT NULL COMMENT '得分值',
  `box` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '人头框，左上右下',
  `person_id` int(10) NULL DEFAULT NULL COMMENT '人物id',
  `trackState` int(2) NULL DEFAULT NULL COMMENT '确认状态：1未确认，2已确认',
  `ip` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '摄像机ip',
  `gate_num` varchar(2) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '闸机编号',
  `gate_status` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '闸机门状态',
  `gate_light_status` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '闸机灯状态',
  `direction` varchar(2) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '方向：0出站，1进站',
  PRIMARY KEY (`uuid`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;