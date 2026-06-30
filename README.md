# TurtleBot3：從零實作 2D LiDAR SLAM

這個專案的目標不是學會啟動 Cartographer、Slam Toolbox 或 Nav2，而是自己完成一套可解釋、可測試的 2D LiDAR SLAM。TurtleBot3 Gazebo 只負責提供機器人、世界、LiDAR、odometry 與模擬時鐘；SLAM 的前端、地圖、回環偵測和後端最佳化都由本專案實作。

## 實作邊界

保留：

- ROS 2 Jazzy：message、topic、rosbag、TF2、launch
- TurtleBot3 Gazebo：模型、感測器與測試世界
- RViz：顯示 scan、pose、map、constraints
- Eigen：矩陣與線性方程運算
- 專案內的 `turtlebot_keyboard`：發布 `/cmd_vel`

自己實作：

- `SE(2)` pose 運算與 Jacobian
- LiDAR filtering、座標轉換和 motion compensation（後期）
- occupancy grid、inverse sensor model、ray tracing
- scan matching 與 pose prediction/fusion
- keyframe/submap 管理
- loop candidate search 與 geometric verification
- pose graph、Gauss-Newton/Levenberg-Marquardt 最佳化
- `map -> odom`、`/map` 和除錯資訊的發布
- 儲存/載入自己的地圖與 graph 格式

明確不使用 `slam_toolbox`、Cartographer、GMapping、Ceres、GTSAM 或 g2o。第一版可以使用 Gazebo 的 `/odom` 作為 noisy motion prior，但不可把 ground-truth pose 當成 SLAM 輸入。

## 最終資料流與模組邊界

```text
Gazebo /scan ----> scan preprocessing -----------+
Gazebo /odom ---> motion prediction              |
                                                   v
                                       local scan matcher
                                             | pose
                                             v
                         occupancy submap <-> keyframe manager
                                             |
                           +-----------------+----------------+
                           v                                  v
                  loop candidate search             pose graph optimizer
                           +-----------------+----------------+
                                             v
                                  corrected trajectory/map
                                             |
                           /map, map->odom, debug markers
```

建議將 ROS adapter 和演算法核心分開。核心不依賴 `rclcpp`，同一份資料可以離線重播並做 deterministic unit test：

```text
src/my_slam/
├── CMakeLists.txt
├── package.xml
├── include/my_slam/
│   ├── math/se2.hpp
│   ├── sensor/laser_scan.hpp
│   ├── mapping/occupancy_grid.hpp
│   ├── matching/correlative_matcher.hpp
│   ├── matching/scan_matcher.hpp
│   ├── graph/pose_graph.hpp
│   └── slam_system.hpp
├── src/
│   ├── core/                    # 不 include ROS header
│   └── ros/slam_node.cpp        # ROS message/TF adapter
├── launch/my_slam.launch.py
├── config/my_slam.yaml
└── test/
```

不要一開始做成許多 ROS nodes。前端與後端先保持為同一 process 內的明確 C++ class；等 profiling 證明需要切分，再決定 concurrency 和 transport。

## 開發順序

### 0. 固定輸入、座標系與評估方式

先啟動模擬：

```bash
cd docker
docker compose up --build -d
docker compose exec turtlebot-develop bash

ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py
```

另一個 shell build 並操作車子：

```bash
cd /home/user/TurtleBot
colcon build --symlink-install
source install/setup.bash
ros2 run turtlebot_keyboard keyboard_controller
```

確認契約：

```bash
ros2 topic hz /scan
ros2 topic echo /scan --once
ros2 topic echo /odom --once
ros2 run tf2_ros tf2_echo odom base_footprint
ros2 run tf2_ros tf2_echo base_link base_scan
```

錄製固定資料，之後每個版本都重播同一份 bag：

```bash
mkdir -p bags
ros2 bag record -o bags/turtlebot3_world /scan /odom /tf /tf_static /clock
```

先定義並寫進測試：pose 記為 `T_A_B`（將 B frame 的點轉至 A frame）；角度一律 rad 並 normalize 至 `[-pi, pi)`。SLAM 估計 `T_map_base`，Gazebo 提供 `T_odom_base`，所以發布：

```text
T_map_odom = T_map_base * inverse(T_odom_base)
```

完成條件：bag 可重播、時間戳正常、TF tree 無多重 publisher，並建立一條不受 SLAM 使用的 ground-truth 評估路徑。評估資料只能計分，不能回灌演算法。

### 1. 先做純 odometry mapping，不做 SLAM

建立 `my_slam` C++ package，先完成：

1. `SE2::compose/inverse/transformPoint` 與對應 unit tests。
2. 將 `LaserScan` 的有效 range 轉成 `base_scan` 中的點。
3. 用 TF static transform 轉到 `base_link`，再用 odometry pose 投影至固定 frame。
4. 實作 bounded 2D log-odds grid。
5. 使用 Bresenham 或 DDA ray tracing：beam 經過位置更新 free，hit endpoint 更新 occupied；`inf`/超出 `range_max` 不可當 occupied hit。
6. 以 `nav_msgs/OccupancyGrid` 發布 `/my_slam/map`。

這一階段故意只做 mapping。若使用已知 pose 都畫不出正確地圖，問題在 sensor model、frame 或時間同步，不應用 scan matcher 掩蓋。

完成條件：固定 bag 重播兩次得到 byte-equivalent grid；直牆不明顯增厚；已知 pose 的 synthetic scan unit test 能生成預期 cell。

### 2. 實作局部 scan matching（前端 v1）

先做容易驗證的 multi-resolution correlative scan matcher：

1. odometry delta 產生 `T_map_base` initial guess。
2. 在 `(x, y, yaw)` search window 內離散搜尋。
3. 將 scan points 投到目前 submap，以 occupancy likelihood 加總作 score。
4. coarse-to-fine 縮小 resolution 和 window。
5. score 未過門檻時拒絕更新，保留 prediction 並標記 degraded。

每一 scan 記錄 initial/final pose、score、搜尋次數和執行時間；在 RViz 畫出 prediction pose、matched pose 及 transformed scan。

完成條件：synthetic transform 可在設定 tolerance 內找回；關閉 odometry 後小範圍仍可追蹤；開啟 odometry prior 後，固定 bag 的 Absolute/Relative Pose Error 比純 odometry 好。

### 3. 實作連續最佳化 scan matcher（前端 v2）

由 occupancy grid 建立 distance/likelihood field，最小化：

```text
E(T) = sum_i robust(distance_field(T * p_i)^2) + odometry_prior(T)
```

自行推導 `SE(2)` Jacobian，以 Gauss-Newton 解 normal equation；加入 robust loss、step limit、收斂條件和 singularity 檢查。correlative matcher 給全域較穩定的初值，continuous matcher 做 sub-cell refinement。

完成條件：用 finite difference 驗證 analytic Jacobian；最佳化每次 accepted iteration 的 cost 不上升；走廊退化場景不產生 NaN 或巨大 pose jump。

### 4. Keyframe 與 submap（前端 v3）

不可永遠把 scan 對整張不斷變動的 global map。加入：

- translation、rotation或時間超過門檻才建立 keyframe
- active submap 固定局部座標原點
- 一個 submap 收到固定數量 keyframes 後 freeze
- scan-to-submap constraint 保存 measurement 與 information matrix
- 地圖由 corrected poses 重建，不在 loop closure 後硬拉舊 grid

完成條件：長 bag 的 scan matching 時間不隨全域地圖面積線性成長；freeze 的 submap 不再被前端修改；trajectory、submap 與 constraint 可序列化並重播。

### 5. 回環偵測

分成兩層，避免「靠近」直接等同回環：

1. Candidate generation：以目前 pose、submap bounding box 或簡單 scan descriptor 找歷史候選，排除最近相鄰 keyframes。
2. Geometric verification：用較大 search window 做 scan-to-frozen-submap matching，score、overlap、translation/rotation 必須通過 gate。

將 accepted/rejected candidate 和原因發布成 Marker 或 log。先在同一個 TurtleBot3 world 繞一圈回到起點，再測試重複走廊造成的 false positive。

完成條件：真正回到起點時至少產生一條正確 non-local constraint；在尚未回訪時不應接受錯誤 constraint；所有 gate 都有單元或 bag regression test。

### 6. Pose graph 後端

graph node 是 keyframe/submap pose，edge 是 odometry、local matching 或 loop constraint。對每條 edge 最小化：

```text
e_ij = Log(inverse(Z_ij) * inverse(X_i) * X_j)
E = sum(e_ij^T Omega_ij e_ij)
```

固定第一個 node 消除 gauge freedom，自行組 sparse/dense normal equation（第一版小圖可 dense），用 Eigen 解線性系統；loop edge 使用 robust kernel。最佳化後重建 trajectory、occupancy map 並更新 `map -> odom`，不要發布 `map -> base_link` 來和既有 TF 衝突。

完成條件：synthetic graph 能收斂到已知解；加入正確 loop edge 後 total error 與 start/end gap 明顯下降；錯誤 loop edge 不會讓整張圖崩潰。

### 7. 整合成 online SLAM node

Node 的最低介面：

| 類型 | 名稱 | 用途 |
|---|---|---|
| subscribe | `/scan` | LiDAR input |
| subscribe | `/odom` | motion prior；之後可替換 |
| TF lookup | `base_link <- base_scan` | sensor extrinsic |
| publish | `/my_slam/map` | occupancy map |
| publish | `/my_slam/pose` | debug pose |
| publish | `/my_slam/path` | corrected trajectory |
| publish TF | `map -> odom` | global correction |
| publish | `/my_slam/constraints` | RViz graph markers |

callback 只做 timestamp validation 與 enqueue。前端順序處理 scan；後端在 snapshot 上最佳化，再以原子方式交換結果，避免 map/trajectory 處於不同 graph revision。

完成條件：online 與相同 bag 的 offline 結果在 tolerance 內一致；`ros2 topic hz`、TF timestamp 與 memory usage 長時間穩定；可在不啟動任何第三方 SLAM package 的情況下完成建圖與回環。

### 8. 評估與工程化

每次固定輸出：

- ATE、RPE、loop start/end gap
- map consistency（牆厚、重影、occupied/free conflict）
- 每 scan latency 的 p50/p95/max
- rejected scans、accepted/rejected loops 數量
- peak memory 和 graph 規模

測試矩陣至少包含：正常速度、快速旋轉、停止後再啟動、scan dropout、odom bias、重複走廊及回到起點。建立一個 `ros2 bag play --clock` regression script；任何參數調整都用同一組 bags 比較，不以「RViz 看起來不錯」作為完成標準。

## 第一輪實作 checklist

- [ ] 建立 `my_slam` package 與 core/ROS adapter 邊界
- [ ] 錄製一圈 `turtlebot3_world` bag，另外保存 ground truth 評估資料
- [ ] 完成 `SE(2)` 與 finite-difference tests
- [ ] 完成 scan conversion、extrinsic 與 timestamp tests
- [ ] 完成 log-odds grid 和 ray tracing tests
- [ ] 先發布純 odometry map，保存 baseline 指標
- [ ] 實作 correlative matcher 和 synthetic tests
- [ ] 加入 continuous matcher 與 Jacobian tests
- [ ] 加入 keyframe/submap
- [ ] 加入 loop detection、pose graph 與 map rebuild
- [ ] 完成固定 bags 的回歸報告

## Docker 內容

image 僅保留 Gazebo/TurtleBot3 simulation、RViz、VNC、ROS 2 build/runtime 與 Eigen。Nav2、Cartographer、Slam Toolbox、官方 TurtleBot3 meta-package 和官方 teleop 都已移除，避免不小心把現成 SLAM/Navigation 帶進依賴樹。

若要確認 image 邊界：

```bash
docker compose build --no-cache
docker compose run --rm --no-deps turtlebot-develop \
  bash -lc "ros2 pkg list | grep -E 'nav2|cartographer|slam_toolbox' && exit 1 || exit 0"
```

`maps/turtlebot3_world.*` 是先前用現成工具產生的參考產物，不是自行實作 SLAM 的輸入。開發期間應由固定 bag 和 ground truth 評估 trajectory 判斷進步，最後再用自己的 map serialization 輸出成果。
