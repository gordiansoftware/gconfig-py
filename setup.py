from setuptools import find_packages, setup

setup(
    name="gconfig",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    author="Koray Gocmen",
    author_email="koray@gordiansoftware.com",
    description="Gordian global config library for Python",
    license="MIT",
    python_requires=">=2.7",
)
