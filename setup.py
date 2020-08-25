import os
from setuptools import setup
import json
import glob

def readme():
    with open('README.rst') as f:
        return f.read()

def package_files(directory):
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            if filename.endswith("~"):
                continue
            paths.append(os.path.join(path, filename))
    print( paths )
    return paths

def get_version():
    with open('version.json') as json_file:
        data = json.load(json_file)

    return "{}.{}.{}".format( data['major'], data['minor'], data['patch'])

def scripts(directory='bin/*py') -> []:
    return glob.glob( directory )


setup(name='tos_api',
      version= get_version(),
      description='ToS-api for galaxy',
      url='https://github.com/usegalaxy-no/tos-api/',
      author='Kim Brugger',
      author_email='kim.brugger@uib.no',
      license='MIT',
      packages=['tos_api', 'kbr'],
      install_requires=[
          'tornado',
          'pycryptodome',
          'psycopg2-binary',
          'munch',
          'records',
          'PyYAML',
          'SQLAlchemy'
      ],
      classifiers=[
        "Development Status :: {}".format( get_version()),
        'License :: MIT License',
        'Programming Language :: Python :: 3'
        ],      
      scripts=scripts(),
#      data_files=[('share/kbr-tools/', package_files('share/'))],
      include_package_data=True,
      zip_safe=False)
