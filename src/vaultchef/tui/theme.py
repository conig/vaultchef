from __future__ import annotations

from .textual import Theme

TUI_THEME_NAME = "vaultchef-ansi"

APP_CSS = """
Screen {
    background: $background;
    color: $text;
    padding: 0;
}

Header, Footer {
    background: $panel;
    color: $text;
}

Footer {
    background: $panel;
    color: $text;
}

Footer:ansi {
    background: $panel;
    color: $text;
}

FooterKey,
FooterLabel,
Footer .footer-key--key,
Footer .footer-key--description,
Footer:ansi .footer-key--key,
Footer:ansi .footer-key--description,
Footer:ansi FooterKey,
Footer:ansi FooterLabel {
    background: $panel;
    color: $text;
}

Footer .footer-key--description,
FooterLabel {
    color: $text;
}

.screen-shell {
    width: 1fr;
    height: 1fr;
    align: center top;
    padding: 1 2;
}

.layout-wide .screen-shell {
    padding: 1 4;
}

.layout-compact .screen-shell {
    padding: 0 1;
}

.screen-card {
    width: 1fr;
    height: auto;
    border: round $panel;
    background: $surface;
    padding: 1 2;
}

.layout-wide .screen-card {
    padding: 2 3;
}

.layout-compact .screen-card,
.density-compact .screen-card {
    padding: 1;
}

#title,
#mode-subtitle {
    text-style: bold;
    color: $text;
}

#mode-actions {
    height: auto;
    align: center middle;
    padding: 1 0;
}

#mode-actions Button {
    margin: 0 1;
}

#create-lists {
    height: 1fr;
}

#tag-list, #recipe-list, #selected-list, #cookbook-list {
    height: 1fr;
    border: round $panel;
    background: $surface;
}

#tag-list:focus,
#recipe-list:focus,
#selected-list:focus,
#cookbook-list:focus {
    border: round $primary;
}

ListView,
ListView > ListItem,
ListView > .list-item,
ListView Label {
    color: $text;
}

ListView > ListItem.--highlight,
ListView > ListItem.-highlight,
ListView > .list-item.--highlight,
ListView > .list-item.-highlight,
ListView > .list-item--highlight {
    background: $panel;
    color: $text;
    text-style: bold;
}

ListView:focus > ListItem.--highlight,
ListView:focus > ListItem.-highlight,
ListView:focus > .list-item.--highlight,
ListView:focus > .list-item.-highlight,
ListView:focus > .list-item--highlight {
    background: ansi_bright_yellow;
    color: ansi_black;
    text-style: bold;
}

ListView > ListItem.cookbook-selected {
    background: ansi_bright_cyan;
    color: ansi_black;
    text-style: bold;
}

ListView:focus > ListItem.--highlight Label,
ListView:focus > ListItem.-highlight Label,
ListView:focus > .list-item.--highlight Label,
ListView:focus > .list-item.-highlight Label,
ListView:focus > .list-item--highlight Label,
ListView > ListItem.cookbook-selected Label {
    color: ansi_black;
}

#status {
    height: auto;
    padding: 1 0 0 0;
    color: $text-muted;
}

#name-input,
#search-input {
    margin: 0 0 1 0;
    background: $surface;
    border: round $panel;
    color: $text;
}

Button {
    background: $surface;
    color: $text;
    border: round $panel;
}

Button.-primary {
    background: $primary;
    color: $button-color-foreground;
    border: round $primary;
}

Button:hover {
    background: $panel;
}

Button.-primary:hover {
    background: $accent;
}

Button:focus {
    background: $primary;
    color: $button-color-foreground;
    border: round $primary;
    text-style: none;
}

Button:focus > .button--label {
    background: transparent;
    color: $button-color-foreground;
    text-style: none;
}

Input {
    background: $surface;
    border: round $panel;
    color: $text;
}

#build-title {
    text-style: bold;
    padding: 1 0 0 0;
}

#build-animation {
    height: auto;
    padding: 1 0 0 0;
    color: $accent;
}

#build-bar {
    height: auto;
    padding: 0 0 1 0;
}

#build-status {
    height: auto;
    color: $text-muted;
}

#build-actions,
#create-actions,
#wizard-nav {
    height: auto;
    padding: 1 0 0 0;
}

#wizard-nav {
    align: left middle;
}

#step-indicator {
    width: 1fr;
    color: $text-muted;
    padding: 0 1;
}

#picker-panel,
#selected-panel {
    height: 1fr;
}

.tex-report-line {
    color: $text-muted;
}

.layout-compact #mode-actions,
.layout-compact #build-actions,
.layout-compact #create-actions,
.layout-compact #wizard-nav,
.layout-compact #create-lists {
    layout: vertical;
}

.layout-compact #mode-actions Button,
.layout-compact #build-actions Button,
.layout-compact #create-actions Button,
.layout-compact #wizard-nav Button {
    margin: 0 0 1 0;
}

.is-hidden {
    display: none;
}
"""

TUI_THEMES = {
    TUI_THEME_NAME: Theme(
        name=TUI_THEME_NAME,
        primary="ansi_bright_cyan",
        secondary="ansi_bright_blue",
        accent="ansi_bright_yellow",
        warning="ansi_bright_yellow",
        error="ansi_bright_red",
        success="ansi_bright_green",
        foreground="ansi_default",
        background="ansi_default",
        surface="ansi_default",
        panel="ansi_bright_black",
        dark=False,
        variables={
            "text": "ansi_default",
            "text-muted": "ansi_bright_black",
            "button-foreground": "ansi_default",
            "button-color-foreground": "ansi_black",
            "button-focus-text-style": "b",
        },
    )
}
