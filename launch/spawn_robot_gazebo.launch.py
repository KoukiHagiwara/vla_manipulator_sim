import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution, Command
from launch_ros.actions import Node
from launch_ros.actions import SetParameter

def generate_launch_description():
    pkg_vla_manipulator = get_package_share_directory('vla_manipulator')
    pkg_vla_manipulator_sim = get_package_share_directory('vla_manipulator_sim')
    moveit_config_dir = get_package_share_directory('vla_manipulator_moveit_config')
    
    # 🌟 URDF直接読み込みを削除し、XACROコマンドで生成する方式に変更！
    xacro_file = os.path.join(moveit_config_dir, 'config', 'so101_new_calib.urdf.xacro')
    robot_desc_cmd = Command(['xacro ', xacro_file, ' hardware_type:=gazebo'])

    workspace_share_dir = os.path.abspath(os.path.join(pkg_vla_manipulator, '..'))
    
    resource_path = os.environ.get('GZ_SIM_RESOURCE_PATH', '')
    set_gz_model_path = SetEnvironmentVariable(name='GZ_SIM_RESOURCE_PATH', value=f'{workspace_share_dir}:{resource_path}')
    
    ign_resource_path = os.environ.get('IGN_GAZEBO_RESOURCE_PATH', '')
    set_ign_model_path = SetEnvironmentVariable(name='IGN_GAZEBO_RESOURCE_PATH', value=f'{workspace_share_dir}:{ign_resource_path}')

    set_sim_time = SetParameter(name='use_sim_time', value=True)
    world_file = os.path.join(pkg_vla_manipulator_sim, 'worlds', 'so101_env.sdf')
    
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([PathJoinSubstitution([FindPackageShare('ros_gz_sim'), 'launch', 'gz_sim.launch.py'])]),
        launch_arguments={'gz_args': f'-r {world_file}'}.items(),
    )

    # 🌟 robot_description に XACRO の実行結果を直接渡す
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='both',
        parameters=[{'robot_description': robot_desc_cmd, 'use_sim_time': True}]
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