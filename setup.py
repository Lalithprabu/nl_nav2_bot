from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'nl_nav2_bot'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Lalith',
    maintainer_email='lalithprabu111@gmail.com',
    description='Natural-language commander for ROS 2 Nav2 navigation.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'nl_command_node = nl_nav2_bot.nl_command_node:main',
            'text_input_node = nl_nav2_bot.text_input_node:main',
        ],
    },
)
