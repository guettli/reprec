import setuptools


setuptools.setup(
    name='reprec',
    version='2016.2',
    license='BSD',
    url='https://github.com/guettli/reprec',
    long_description=open('README.rst').read(),
    packages=setuptools.find_packages(),
    include_package_data=True,

    entry_points={
        'console_scripts': [  
		'reprec=reprec.reprec:main'
        ],
    }
)
