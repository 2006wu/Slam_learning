from setuptools import find_packages, setup

package_name = 'turtlebot_keyboard'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    tests_require=['pytest'],
    zip_safe=True,
    maintainer='user',
    maintainer_email='user@example.com',
    description='Fixed-speed keyboard controller for TurtleBot3.',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'keyboard_controller = '
            'turtlebot_keyboard.keyboard_controller:main',
        ],
    },
)
