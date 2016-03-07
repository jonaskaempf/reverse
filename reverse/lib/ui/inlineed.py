#!/usr/bin/env python3
#
# Reverse : Generate an indented asm code (pseudo-C) with colored syntax.
# Copyright (C) 2015    Joel
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.    If not, see <http://www.gnu.org/licenses/>.
#

from curses import A_UNDERLINE, color_pair

from reverse.lib.custom_colors import *
from reverse.lib.ui.window import Window


# TODO: not very clean class...


class InlineEd(Window):
    def __init__(self, window, h, w, line, xbegin, idx_token, text,
                 is_new_token, color, tok_line, do_nothing=False, prefix=""):
        # The window class is only used for the read_escape_keys
        Window.__init__(self, None, has_statusbar=True)

        self.mapping = {
            b"\x1b\x5b\x44": self.k_left,
            b"\x1b\x5b\x43": self.k_right,
            b"\x7f": self.k_backspace,
            b"\x1b\x5b\x37\x7e": self.k_home,
            b"\x1b\x5b\x38\x7e": self.k_end,
            b"\x1b\x5b\x33\x7e": self.k_delete,
            b"\x15": self.k_ctrl_u,
            b"\x0b": self.k_ctrl_k,
            b"\n": self.k_save,
            b"\x01": self.k_home, # ctrl-a
            b"\x05": self.k_end, # ctrl-e
        }

        self.print_curr_line = True

        self.xbegin = xbegin
        self.idx_token = idx_token
        self.par = window # parent == main window
        self.text = list(text)
        self.is_new_token = is_new_token
        self.line = line
        self.color = color
        self.tok_line = tok_line
        self.do_nothing = do_nothing
        self.prefix = prefix

        self.par.cursor_x = self.xbegin
        if self.prefix:
            self.par.cursor_x += len(self.prefix) + 1


    def start_view(self, screen):
        self.screen = screen
        y = self.par.cursor_y

        i = 0  # index of the cursor in self.text

        while 1:
            (h, w) = screen.getmaxyx()

            if self.has_statusbar:
                h -= 1 # status bar

            self.screen.move(y, 0)
            self.screen.clrtoeol()
            self.print_line(w, y)

            if self.par.cursor_x >= w:
                self.par.cursor_x = w - 1
            screen.move(y, self.par.cursor_x)
            k = self.read_escape_keys()

            if k == b"\x1b": # escape = cancel
                break

            if k in self.mapping:
                i = self.mapping[k](i, w)
                if k == b"\n":
                    return True

            # Ascii characters
            elif k and k[0] >= 32 and k[0] <= 126 and self.par.cursor_x < w - 1:
                # TODO: fix cursor_x >= w
                # TODO: utf-8
                c = chr(k[0])
                self.text.insert(i, c)
                i += 1
                self.par.cursor_x += 1

        return False


    def print_line(self, w, y):
        is_current_line = True
        force_exit = False
        x = 0
        i = 0
        printed = False # the string currently edited

        while i < len(self.tok_line) or not printed:
            if not printed and i == self.idx_token:
                string = "".join(self.text)
                if self.prefix:
                    string = " " + self.prefix + string
                col = self.color
                is_bold = False
                printed = True
                if not self.is_new_token:
                    i += 2 # token space + comment
            else:
                (string, col, is_bold) = self.tok_line[i]
                i += 1

            if x + len(string) >= w:
                string = string[:w-x-1]
                force_exit = True

            c = color_pair(col)

            if is_current_line and self.print_curr_line:
                c |= A_UNDERLINE

            if is_bold:
                c |= curses.A_BOLD

            self.screen.addstr(y, x, string, c)

            x += len(string)
            if force_exit:
                break

        if is_current_line and not force_exit and self.print_curr_line:
            n = w - x - 1
            self.screen.addstr(y, x, " " * n, color_pair(0) | A_UNDERLINE)
            x += n


    def k_left(self, i, w):
        if i != 0:
            i -= 1
            self.par.cursor_x -= 1
        return i

    def k_right(self, i, w):
        if i != len(self.text):
            i += 1
            self.par.cursor_x += 1
            # TODO: fix cursor_x >= w
            if self.par.cursor_x >= w:
                i -= self.par.cursor_x - w + 1
                self.par.cursor_x = w - 1
        return i

    def k_backspace(self, i, w):
        if i != 0:
            del self.text[i-1]
            i -= 1
            self.par.cursor_x -= 1
        return i

    def k_home(self, i, w):
        self.par.cursor_x = self.xbegin
        if self.prefix:
            self.par.cursor_x += len(self.prefix)
        return 0

    def k_end(self, i, w):
        n = len(self.text)
        self.par.cursor_x = self.xbegin + n
        if self.prefix:
            self.par.cursor_x += len(self.prefix)
        i = n
        # TODO: fix cursor_x >= w
        if self.par.cursor_x >= w:
            i -= self.par.cursor_x - w + 1
            self.par.cursor_x = w - 1
        return i

    def k_delete(self, i, w):
        if i != len(self.text):
            del self.text[i]
        return i

    def k_save(self, i, w):
        if self.do_nothing:
            return

        lines = self.par.output.lines
        token_lines = self.par.token_lines

        idx_token = self.idx_token
        xbegin = self.xbegin
        line = self.line

        if self.is_new_token:
            # Extract the rest of the lines (everything after the new string)
            off = xbegin + len(self.text) + 1
            if self.prefix:
                off += len(self.prefix) + 1
            after = lines[line][:]
        else:
            after = lines[line][xbegin + 1:]

        if not self.text:
            # Remove the text
            if not self.is_new_token:
                lines[line] = "".join([
                    lines[line][:xbegin],
                    " ",
                    after])

                # Remove the space before the comment and the comment
                del token_lines[line][idx_token]
                del token_lines[line][idx_token]

            return

        # Modify the text

        self.text = "".join(self.text)

        if self.is_new_token:
            # Space token
            token_lines[line].insert(idx_token, (" ", 0, False))

            # Insert the new token
            token_lines[line].insert(idx_token + 1,
                    (self.prefix + self.text, self.color, False))

        else:
            # Plus 1 for the space token
            token_lines[line][idx_token + 1] = \
                    (self.prefix + self.text, self.color, False)

        lines[line] = "".join([
            lines[line][:xbegin],
            " " + self.prefix,
            self.text,
            " ",
            after])


    def k_ctrl_u(self, i, w):
        self.text = self.text[i:]
        self.par.cursor_x = self.xbegin
        if self.prefix:
            self.par.cursor_x += len(self.prefix)
        return 0

    def k_ctrl_k(self, i, w):
        self.text = self.text[:i]
        return i
