import setuptools

# 自述文件
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

# 模块依赖
with open('requirements.txt', 'r', encoding='utf-8') as f:
    requirements = f.read().splitlines()

setuptools.setup(
    name='yolo-to-mongo',
    version=1.2,
    author='Hekaiyou',
    author_email='hekaiyou@qq.com',
    description='YOLO to MongoDB',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/hekaiyou/yolo_to_mongo',
    # packages=setuptools.find_packages(),
    py_modules=['main'],
    include_package_data=True,
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    install_requires=requirements,
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'yolo-to-mongo=main:main'
        ],
    }
)
