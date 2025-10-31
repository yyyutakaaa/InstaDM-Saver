"""Setup script for Instagram DM Saver."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file, "r", encoding="utf-8") as f:
        requirements = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#")
        ]

setup(
    name="instagram-dm-saver",
    version="2.0.0",
    author="Instagram DM Saver Team",
    author_email="",
    description="Fetch and save your Instagram direct messages with advanced features",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/InstaDM-Saver",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Communications :: Chat",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "flake8>=6.1.0",
            "mypy>=1.5.0",
        ],
        "gui": [
            "customtkinter>=5.0.0",
            "pillow>=10.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "instagram-dm-saver=instagram_dm_saver.cli:main",
            "igdm=instagram_dm_saver.cli:main",
            "instagram-dm-saver-gui=instagram_dm_saver.gui:main",
            "igdm-gui=instagram_dm_saver.gui:main",
        ],
    },
    include_package_data=True,
    package_data={
        "instagram_dm_saver": ["py.typed"],
    },
    zip_safe=False,
    keywords="instagram dm direct-messages chat backup export",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/InstaDM-Saver/issues",
        "Source": "https://github.com/yourusername/InstaDM-Saver",
        "Documentation": "https://github.com/yourusername/InstaDM-Saver/blob/main/README.md",
    },
)
