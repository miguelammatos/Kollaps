from setuptools import setup

setup(name='need',
      version='1.1',
      description='Decentralized network emulator',
      url='https://github.com/joaoneves792/NEED',
      author='Joao Neves',
      packages=['need', 'need.NEEDlib', 'need.TCAL'],
      install_requires=[
          'dnspython',
      ],
      include_package_data=True,
      package_data={
          'need.TCAL':['libTCAL.so'],
      },
      entry_points = {
          'console_scripts': ['deploymentGenerator=need.deploymentGenerator:main']
      },
      zip_safe=False)
