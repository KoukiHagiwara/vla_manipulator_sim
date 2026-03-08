import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.actions import SetParameter

def generate_launch_description():
    # パッケージのパスを取得
    pkg_vla_manipulator = get_package_share_directory('vla_manipulator')
    pkg_vla_manipulator_sim = get_package_share_directory('vla_manipulator_sim')

    #moveitとの連携
    moveit_config_dir = get_package_share_directory('vla_manipulator_moveit_config')
    


    # URDFファイルのパス
    urdf_file = os.path.join(pkg_vla_manipulator, 'models', 'robot.urdf')
    with open(urdf_file, 'r') as infp:
        robot_desc = infp.read()

    robot_desc = robot_desc.replace('$(find vla_manipulator_sim)', pkg_vla_manipulator_sim)
    # 🌟 過去の成功コードを参考に、モデルへのパスを確実にする
    # workspace_share_dir は ~/ros2_ws/install/share になります
    workspace_share_dir = os.path.abspath(os.path.join(pkg_vla_manipulator, '..'))
    
    # Fortress環境で確実に見つけられるよう、GZとIGNの両方をSetEnvironmentVariableで設定
    resource_path = os.environ.get('GZ_SIM_RESOURCE_PATH', '')
    set_gz_model_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH', 
        value=f'{workspace_share_dir}:{resource_path}'
    )
    
    ign_resource_path = os.environ.get('IGN_GAZEBO_RESOURCE_PATH', '')
    set_ign_model_path = SetEnvironmentVariable(
        name='IGN_GAZEBO_RESOURCE_PATH', 
        value=f'{workspace_share_dir}:{ign_resource_path}'
    )

    # このLaunchファイルで起動する「全て」のノードにシミュレーション時間を強制する
    set_sim_time = SetParameter(name='use_sim_time', value=True)

    world_file = os.path.join(pkg_vla_manipulator_sim, 'worlds', 'so101_env.sdf')
    # 1. Gazebo の起動 (過去の成功コードと全く同じ構文)
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('ros_gz_sim'),
                'launch',
                'gz_sim.launch.py'
            ])
        ]),
        launch_arguments={
            'gz_args': f'-r {world_file}',
        }.items(),
    )

    # 2. Robot State Publisher
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='both',
        parameters=[{'robot_description': robot_desc, 'use_sim_time': True}]
    )

    # 3. Gazeboにロボットをスポーンさせるノード
    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'so101',
            '-topic', 'robot_description',
        ],
        output='screen',
    )
    
    # 🌟 シミュレーション時間をROS 2に同期させるブリッジ
    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock'],
        output='screen'
    )

    # カメラ映像等のブリッジ
    bridge_params = os.path.join(pkg_vla_manipulator_sim, 'config', 'bridge.yaml')
    ros_gz_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=[
            '--ros-args',
            '-p',
            f'config_file:={bridge_params}',
        ],
        output='screen'
    )

    # 🌟 追加2：コントローラを起動する司令塔たち
    jsb_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster"],
    )
    arm_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["arm_controller"],
    )
    gripper_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["gripper_controller"],
    )

    # =======================================================
    # 🌟 追加：MoveIt本体 と RViz をシミュレーション時間で起動！
    # =======================================================
    move_group = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(moveit_config_dir, 'launch', 'move_group.launch.py')
        ),
        launch_arguments={'use_sim_time': 'true'}.items()
    )

    rviz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(moveit_config_dir, 'launch', 'moveit_rviz.launch.py')
        ),
        launch_arguments={'use_sim_time': 'true'}.items()
    )

    return LaunchDescription([
        set_sim_time,
        set_gz_model_path,
        set_ign_model_path,
        gz_sim,
        robot_state_publisher,
        spawn,
        clock_bridge,
        ros_gz_bridge,
        jsb_spawner,
        arm_spawner,
        gripper_spawner,
        move_group,  
        rviz
    ])