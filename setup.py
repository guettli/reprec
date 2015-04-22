import setuptools


setuptools.setup(
    name='reprec',
    version='2015.1',
    license='BSD',
    long_description=open('README.txt').read(),
    packages=setuptools.find_packages(),
    install_requires=[
    ],
    include_package_data=True,

    entry_points={
        'console_scripts': [  
		'reprec= reprec:main'   
        ],
    }
)
