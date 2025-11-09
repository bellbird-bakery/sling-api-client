"""Setup configuration for sling-api-client package."""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="sling-api-client",
    version="0.1.0",
    author="Your Organization",
    author_email="platform-team@yourcompany.com",
    description="Python client for the Sling scheduling API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/sling-api-client",
    packages=find_packages(exclude=["tests", "tests.*", "examples", "examples.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Office/Business :: Scheduling",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "responses>=0.22.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
        ],
        "django": [
            "django>=4.0",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
