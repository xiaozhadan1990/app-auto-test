from __future__ import annotations

from tests.lysora.pages.ios._base import IOSLysoraPage


class IOSLysoraDemoExperiencePage(IOSLysoraPage):
    feature_name = "Lysora Demo Experience page"

    def open_project_tab(self) -> None:
        self._not_implemented()

    def open_demo_experience(self) -> None:
        self._not_implemented()

    def open_smb_cctv_demo(self) -> None:
        self._not_implemented()

    def create_demo_project(self) -> None:
        self._not_implemented()

    def wait_and_assert_smb_project_exists(self, wait_seconds: int = 10) -> None:
        self._not_implemented()
