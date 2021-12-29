#!/usr/bin/env python3
from setuptools import setup

# skill_id=package_name:SkillClass
PLUGIN_ENTRY_POINT = 'skill-simple-youtube.jarbasai=skill_simple_youtube:SimpleYoutubeSkill'

setup(
    # this is the package name that goes on pip
    name='skill-simple-youtube',
    version='0.0.1',
    description='ovos common play youtube skill plugin',
    url='https://github.com/JarbasSkills/skill-simple-youtube',
    author='JarbasAi',
    author_email='jarbasai@mailfence.com',
    license='Apache-2.0',
    package_dir={"skill_simple_youtube": ""},
    package_data={'skill_simple_youtube': ['locale/*', 'ui/*']},
    packages=['skill_simple_youtube'],
    include_package_data=True,
    install_requires=["ovos-plugin-manager>=0.0.1a3",
                      "tutubo",
                      "ovos_workshop~=0.0.5a1"],
    keywords='ovos skill plugin',
    entry_points={'ovos.plugin.skill': PLUGIN_ENTRY_POINT}
)
