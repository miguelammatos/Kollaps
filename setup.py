from setuptools import setup

setup(name='need',
      version='2.0',
      description='Decentralized network emulator',
      url='https://github.com/miguelammatos/NEED.git',
      author='Joao Neves, Paulo Gouveia',
      packages=['need', 'need.NEEDlib', 'need.TCAL'],
      install_requires=[
          'dnspython',
      ],
      include_package_data=True,
      package_data={
          'need.TCAL': ['libTCAL.so'],
          'need': ['static/css/*', 'static/js/*',  'templates/*.html'],
      },
      entry_points={
          'console_scripts': ['NEEDdeploymentGenerator=need.deploymentGenerator:main',
                              'NEEDDashboard=need.Dashboard:main',
                              'NEEDemucore=need.emucore:main',
                              'NEEDbootstrapper=need.bootstrapper:main'],
      },
      zip_safe=False)
