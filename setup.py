import os

from setuptools import find_packages, setup

with open("README.md") as readme_file:
    README = readme_file.read()

setup_args = {
    "name": "spctrl",
    "version": os.environ["BUILD_VERSION"],
    "description": "Simple Process Controller",
    "long_description_content_type": "text/markdown",
    "long_description": README,
    "license": "MIT",
    "packages": find_packages(where="src", include=["spctrl", "spctrl.*"]),
    "author": "Jesse Reichman",
    "keywords": ["Simple", "Process", "Controller", "Supervisor"],
    "url": "https://github.com/archmachina/spctrl",
    "download_url": "https://pypi.org/project/spctrl/",
    "entry_points": {"console_scripts": ["spctrl = spctrl.cli:main"]},
    "package_dir": {"": "src"},
    "install_requires": ["PyYAML>=6.0.0", "Jinja2>=3.1.0", "obslib>=0.1.1"],
}

if __name__ == "__main__":
    setup(**setup_args, include_package_data=True)
