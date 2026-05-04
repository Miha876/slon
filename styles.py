"""Application stylesheet."""


def build_stylesheet() -> str:
    """Build and return the complete stylesheet for the application."""
    return """
        QWidget {
            color: #0f172a;
            font-family: "Segoe UI", "Segoe UI Variable";
        }

        #shell, #adminPage {
            background: #07529c;
        }

        #tabs {
            background: #074782;
            border-bottom: 1px solid rgba(255, 255, 255, 0.40);
            min-height: 40px;
            max-height: 40px;
        }

        #tabActive, #tabInactive {
            background: transparent;
            border: none;
            border-radius: 0;
            font-size: 15px;
            padding: 10px 8px 9px 8px;
            text-align: left;
        }

        #tabActive {
            color: #ffffff;
            border-bottom: 2px solid #ffffff;
        }

        #tabInactive {
            color: #9dc4ef;
        }

        #videoPanel {
            background: #0c121d;
            border-radius: 7px;
        }

        #cameraCard {
            background: #0c121d;
            border: 1px solid #111a29;
            border-radius: 5px;
        }

        #cameraCard:hover {
            border: 1px solid #2f6fb6;
        }

        #cameraTitle {
            color: #ffffff;
            font-size: 13px;
            font-weight: 700;
        }

        #cameraStatus {
            color: #95a3b8;
            font-size: 12px;
            font-weight: 500;
        }

        #videoSurface {
            background: #0c121d;
            border: none;
            border-radius: 0;
            color: #95a3b8;
            font-size: 14px;
        }

        #sidebar {
            background: #f1f4f8;
            border-radius: 8px;
            border: 4px solid #9fc4ee;
        }

        #statusBanner {
            background: #d4deec;
            border: 2px solid #b8c7dc;
            border-radius: 5px;
            color: #111827;
            font-size: 15px;
            font-weight: 700;
            min-height: 44px;
        }

        #adminPage #adminLabel,
        #dialogLabel {
            color: #f8fafc;
            font-size: 15px;
        }

        #sidebar #infoText, #sidebar #sectionTitle {
            color: #111827;
            font-size: 15px;
        }

        #featuresTable {
            background: #ffffff;
            border: none;
            color: #111827;
            font-size: 14px;
        }

        #featuresTable::item {
            padding-left: 10px;
            min-height: 30px;
        }

        QHeaderView::section {
            background: #d3deed;
            border: none;
            color: #111827;
            font-size: 12px;
            font-weight: 700;
            min-height: 38px;
        }

        #summary {
            color: #475569;
            font-size: 13px;
        }

        #snapshotButton, #adminButton, #primaryButton, #secondaryButton {
            background: #2e69bd;
            border: none;
            border-radius: 7px;
            color: #ffffff;
            font-size: 15px;
            font-weight: 700;
            min-height: 38px;
            padding: 0 14px;
        }

        #snapshotButton:hover, #adminButton:hover, #primaryButton:hover, #secondaryButton:hover, #smallButton:hover {
            background: #3978cf;
        }

        #errorButton {
            background: #c91f25;
            border: none;
            border-radius: 7px;
            color: #ffffff;
            font-size: 15px;
            font-weight: 700;
            min-height: 38px;
            padding: 0 14px;
        }

        #errorButton:hover {
            background: #e12a30;
        }

        #adminInput, #passwordInput, QComboBox, QSpinBox {
            background: #134f8d;
            border: 1px solid #2b6fb3;
            border-radius: 5px;
            color: #ffffff;
            min-height: 27px;
            padding: 0 8px;
        }

        #adminInput:focus,
        #passwordInput:focus,
        QComboBox:focus,
        QSpinBox:focus {
            border: 1px solid #a7d8ff;
        }

        #smallButton {
            background: #2e69bd;
            border: none;
            border-radius: 5px;
            color: #ffffff;
            font-weight: 800;
            min-width: 34px;
            min-height: 27px;
        }

        #adminStatus {
            color: #d8e9ff;
            font-size: 15px;
        }

        #logs {
            background: #252525;
            border: 1px solid #3a3a3a;
            border-radius: 4px;
            color: #ffffff;
            font-family: Consolas, "Courier New";
            font-size: 12px;
        }

        QDialog {
            background: #1f1f24;
        }

        QDialog QLabel {
            color: #f8fafc;
            font-size: 14px;
        }

        QLineEdit::placeholder {
            color: #b8c7dc;
        }

        #messageDialog {
            background: #f8fafc;
        }

        #messageTitle {
            color: #0f172a;
            font-size: 17px;
            font-weight: 800;
        }

        #messageBody {
            color: #334155;
            font-size: 14px;
            line-height: 1.35;
        }

        #infoBadge {
            background: #2e69bd;
            border-radius: 21px;
            color: #ffffff;
            font-size: 22px;
            font-weight: 800;
        }

        #warningBadge {
            background: #f59e0b;
            border-radius: 21px;
            color: #111827;
            font-size: 22px;
            font-weight: 900;
        }

        #messageButton {
            background: #2e69bd;
            border: none;
            border-radius: 7px;
            color: #ffffff;
            font-size: 14px;
            font-weight: 800;
            min-width: 104px;
            min-height: 34px;
            padding: 0 16px;
        }

        #messageButton:hover {
            background: #3978cf;
        }

        #messageButton:pressed {
            background: #24549a;
        }

        #statusDotOnline {
            background: #22c55e;
            border-radius: 5px;
        }

        #statusDotOffline {
            background: #ef4444;
            border-radius: 5px;
        }
    """
