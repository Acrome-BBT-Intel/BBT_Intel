from setuptools import setup, find_packages

requirements = ['evdev','pigpio']

setup(
    name='embedded_pi',
    version='0.1.0',
    description="",
    url='',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    packages=find_packages(exclude=[]),
    install_requires=requirements,
)
