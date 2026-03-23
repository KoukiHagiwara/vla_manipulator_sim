## 実行方法
1. GazeboとMoveIt(vla_manipulator_moveit_configパッケージ)の起動
```
$  ros2 launch vla_manipulator_sim spawn_robot_gazebo.launch.py
```

- Gazeboで学習がうまくいっているか試すコマンド
1. Gazeboの起動
```
$  ros2 launch vla_manipulator_sim spawn_robot_gazebo.launch.py
```
2. MoveItの起動
```
$  ros2 launch vla_manipulator_moveit_config demo.launch.py use_sim_time:=true
```
3. AIノードの起動
```
$  cd lerobot
```
```
$  pixi run python act_inference_node.py
```