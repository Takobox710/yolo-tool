from __future__ import annotations

STYLE = """
QWidget { font-family: "Microsoft YaHei UI"; font-size: 14px; color: #14233A; }
#nav { background: #26394D; }
#brand { color: white; font-size: 24px; font-weight: 700; }
#navButton { color: white; background: transparent; border: 0; padding: 10px 14px; font-weight: 700; font-size: 17px; }
#navButton:checked, #navButton:hover { background: #344D66; border-radius: 6px; }
#dataSidebar { background: #26394D; border-radius: 8px; }
#dataSidebarTitle { color: white; font-size: 24px; font-weight: 700; padding: 4px 0 10px 0; }
#dataSidebarDivider { color: #536779; background: #536779; max-height: 1px; }
#dataNavButton { color: white; background: transparent; border: 0; padding: 10px 8px; text-align: left; font-size: 16px; }
#dataNavButton:checked, #dataNavButton:hover { background: #344D66; border-radius: 5px; }
#annotationSidebar { background: #26394D; border-radius: 8px; }
#annotationIcon { color: white; font-size: 30px; font-weight: 700; }
#annotationTitle { color: white; font-size: 24px; font-weight: 700; padding: 4px 0 10px 0; }
#annotationDivider { color: #536779; background: #536779; max-height: 1px; }
#annotationToolButton { color: white; background: transparent; border: 0; padding: 10px 8px; text-align: left; font-size: 16px; }
#annotationToolButton[compactArrowButton="true"] { padding-left: 6px; }
#annotationToolButton:hover { background: #344D66; border-radius: 5px; }
#annotationToolButton:disabled { color: #92A0AF; background: transparent; }
#annotationCanvas { background: #F3F6FA; border: 1px solid #D9E3EC; border-radius: 3px; }
#annotationRightPanel { background: transparent; }
#annotationPathLabel { color: #14233A; font-size: 16px; }
#annotationPrimaryButton { background: #26394D; color: white; border: 0; border-radius: 4px; padding: 9px 10px; }
#annotationPrimaryButton:hover { background: #344D66; }
#stack { background: #EEF2F6; }
#card { background: white; border: 1px solid #D9E3EC; border-radius: 8px; }
#pageTitle { color: #1A3857; font-size: 28px; font-weight: 700; }
#sectionTitle { color: #18344F; font-size: 18px; font-weight: 700; }
#metricValue { color: #0D2B49; font-size: 16px; font-weight: 700; }
#statValue { color: #0D2B49; font-size: 14px; font-weight: 700; }
#fieldLabel { color: #627286; font-size: 12px; }
#helpText { color: #627286; font-size: 12px; line-height: 18px; }
#inlineFieldLabel { color: #14233A; font-size: 14px; font-weight: 400; }
#imageView { background: #F8FBFD; border: 1px solid #D9E3EC; border-radius: 6px; color: #627286; }
#statCard { background: #F5F8FB; border: 1px solid #E8EDF2; border-radius: 6px; }
#metricCard { background: #F5F8FB; border: 1px solid #E8EDF2; border-radius: 6px; }
#chartView { background: white; border: 0; }
#systemInfoOuter { background: white; border: 1px solid #D9E3EC; border-radius: 8px; }
#systemInfoInner { background: #F0F2F5; border: 1px solid #E0E3E8; border-radius: 6px; }
QLineEdit, QTextEdit, QComboBox, QTableWidget { background: white; border: 1px solid #CFD9E3; border-radius: 5px; padding: 7px; }
QTableWidget { background: #FFFFFF; alternate-background-color: #F7FAFC; gridline-color: #E1E8F0; selection-background-color: #DCEEFF; selection-color: #0D2B49; }
QTableWidget::item { padding: 6px; border-bottom: 1px solid #E8EDF2; }
QTableWidget::item:hover { background: #EEF6FF; }
QHeaderView::section { background: #EAF1F8; color: #0D2B49; border: 0; border-right: 1px solid #D8E2EC; border-bottom: 1px solid #CBD8E4; padding: 7px 6px; font-weight: 700; }
QHeaderView::up-arrow { image: none; width: 0px; height: 0px; }
QHeaderView::down-arrow { image: none; width: 0px; height: 0px; }
QPushButton { background: #208FD4; color: white; border: 0; border-radius: 5px; padding: 9px 14px; }
QPushButton:hover { background: #1A7ABF; }
QPushButton#softButton { background: #F5F8FB; color: #14233A; border: 1px solid #D9E3EC; }
QPushButton#softButton:hover { background: #E8EDF2; border-color: #B8C4D0; }
QPushButton#compactSoftButton { background: #F5F8FB; color: #14233A; border: 1px solid #D9E3EC; border-radius: 5px; padding: 4px 10px; font-size: 14px; }
QPushButton#compactSoftButton:hover { background: #E8EDF2; border-color: #B8C4D0; }
QPushButton:disabled { background: #C0CCD8; color: #8899AA; }
QTabWidget::pane { border: 1px solid #D9E3EC; background: white; border-radius: 6px; }
QTabBar::tab { padding: 9px 16px; background: #F5F8FB; border: 1px solid #D9E3EC; }
QTabBar::tab:selected { background: white; color: #208FD4; }
QToolTip { background: #14233A; color: white; border: 0; border-radius: 4px; padding: 6px 8px; }
"""
