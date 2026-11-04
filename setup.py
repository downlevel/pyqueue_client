from setuptools import setup, find_packages

# Read README file for long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pyqueue-client",
    version="1.2.1",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.0",
        "urllib3>=1.26.0"
    ],
    description="Python client library for adding messages to PyQueue with local and remote support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Mauro Giulivi",
    url="https://github.com/downlevel/pyqueue_client",
    project_urls={
        "Source": "https://github.com/downlevel/pyqueue_client",
        "Issues": "https://github.com/downlevel/pyqueue_client/issues",
        "Server": "https://github.com/downlevel/pyqueue-server",
    },
    keywords=["queue", "message-queue", "sqs", "job-queue", "task-queue", "pyqueue"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Distributed Computing",
    ],
    python_requires=">=3.6",
)