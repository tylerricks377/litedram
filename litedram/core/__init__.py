#
# This file is part of LiteDRAM.
#
# Copyright (c) 2016-2019 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

from migen import *

from litex.soc.interconnect.csr import AutoCSR, CSRStorage, CSRStatus

from litedram.dfii import DFIInjector
from litedram.core.controller import ControllerSettings, LiteDRAMController
from litedram.core.crossbar import LiteDRAMCrossbar

# Core ---------------------------------------------------------------------------------------------

class LiteDRAMCore(Module, AutoCSR):
    def __init__(self, phy, geom_settings, timing_settings, clk_freq, **kwargs):
        self.submodules.dfii = DFIInjector(
            addressbits   = max(geom_settings.addressbits, getattr(phy, "addressbits", 0)),
            bankbits      = max(geom_settings.bankbits, getattr(phy, "bankbits", 0)),
            nranks        = phy.settings.nranks,
            databits      = phy.settings.dfi_databits,
            nphases       = phy.settings.nphases,
            is_clam_shell = phy.settings.is_clam_shell)
        self.comb += self.dfii.master.connect(phy.dfi)

        self.trefi = Signal(32, reset=timing_settings.tREFI)
        self.refresh_csr = CSRStatus(32)
        self.refresh_enable = Signal(1, reset=1)
        self.auto_precharge_csr = Signal(1)
        self.submodules.controller = controller = LiteDRAMController(
            phy_settings       = phy.settings,
            geom_settings      = geom_settings,
            timing_settings    = timing_settings,
            clk_freq           = clk_freq,
            trefi              = self.trefi,
            refresh_csr        = self.refresh_csr,
            refresh_enable     = self.refresh_enable,
            auto_precharge_csr = self.auto_precharge_csr,
            **kwargs)
        self.comb += controller.dfi.connect(self.dfii.slave)

        self.submodules.crossbar = LiteDRAMCrossbar(controller.interface)
