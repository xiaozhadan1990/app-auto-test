from __future__ import annotations

from tests.reyee.pages.ios._base import IOSReyeePage


class IOSReyeeProjectPage(IOSReyeePage):
    feature_name = "Reyee Project page"

    def open_project_tab(self) -> None:
        self._not_implemented()

    def open_virtual_experience(self) -> None:
        self._not_implemented()

    def open_common_scene(self) -> None:
        self._not_implemented()

    def create_virtual_project(self) -> None:
        self._not_implemented()

    def assert_project_visible(self, project_keyword: str = "通用场景") -> None:
        self._not_implemented()

    def open_project_more_menu(self) -> None:
        self._not_implemented()

    def click_delete_project(self) -> None:
        self._not_implemented()

    def confirm_delete_project(self) -> None:
        self._not_implemented()

    def assert_project_not_exists(self, project_keyword: str = "通用场景") -> None:
        self._not_implemented()
