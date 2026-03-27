import pytest

from tests.lysora.flows.demo_experience_flow import LysoraDemoExperienceFlow


@pytest.mark.smoke
@pytest.mark.lysora
@pytest.mark.case_name("Lysora 创建Demo Project")
@pytest.mark.case_priority(3)
def test_lysora_demo_experience_create_demo_project(driver, lysora_app_id):
    LysoraDemoExperienceFlow(driver).run_create_demo_project_flow(app_id=lysora_app_id)
