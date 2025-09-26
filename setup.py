"""Setup script for CCN Minimal EPN Cycle."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="ccn-minimal-epn",
    version="0.1.0",
    author="CCN Development Team",
    author_email="dev@ccn.ai",
    description="Minimal EPN cycle implementation for CCN with Groq integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ccn-ai/minimal-epn",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "ccn-minirun=ccn_minirun:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["schemas/*.json"],
    },
    project_urls={
        "Bug Reports": "https://github.com/ccn-ai/minimal-epn/issues",
        "Source": "https://github.com/ccn-ai/minimal-epn",
    },
)