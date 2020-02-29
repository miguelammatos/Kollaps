
from setuptools import setup

setup(name='kollaps',
      version='1.0',
      description='Decentralized network emulator',
      url='https://github.com/miguelammatos/Kollaps.git',
      author='Joao Neves, Paulo Gouveia, Luca Liechti',
      packages=[
          'kollaps',
          'kollaps.Kollapslib.deploymentGenerators',
          'kollaps.Kollapslib.bootstrapping',
          'kollaps.Kollapslib.ThunderStorm',
          'kollaps.Kollapslib',
          'kollaps.TCAL'
      ],
      install_requires=[
          'dnspython',
          'docker',
          'kubernetes',
          'netifaces',
          'ply'
      ],
      include_package_data=True,
      package_data={
          'kollaps.TCAL': ['libTCAL.so'],
          'kollaps': ['static/css/*', 'static/js/*',  'templates/*.html'],
      },
      entry_points={
          'console_scripts': ['KollapsDeploymentGenerator=kollaps.deploymentGenerator:main',
                              'KollapsDashboard=kollaps.Dashboard:main',
                              'KollapsLogger=kollaps.Logger:main',
                              'KollapsEmulationManager=kollaps.EmulationManager:main',
                              'Kollapsbootstrapper=kollaps.bootstrapper:main',
                              'ThunderstormTranslator=kollaps.ThunderstormTranslator:main'],
      },
      zip_safe=False)
      
