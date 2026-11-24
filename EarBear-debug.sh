#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
export PYTHONUNBUFFERED=1 PYTHONFAULTHANDLER=1
exec "$(dirname -- "$0")/EarBear" "$@"
