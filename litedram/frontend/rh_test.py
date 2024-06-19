"""
A self-made implementation of a rowhammer-test state machine.
"""


from migen import *

from litex.soc.interconnect.csr import *

from litedram.common import LiteDRAMNativePort



"""
Constants
"""

ONE_BIT_WIDE = 1
TWO_BITS_WIDE = 2
WIDTH_32_BITS = 32
WIDTH_64_BITS = 64



class Row_Hammer_Test(Module, AutoCSR):

    def __init__(self, rw_test_port : LiteDRAMNativePort, sys_clk_freq : int):

        self.rw_test_port = rw_test_port

        """
        CSR Registers
        """

        # Control the number of rows and the frequency of attacking them
        self.addr_to_set_val_csr = CSRStorage(rw_test_port.address_width, description="The row to attack in the DRAM")
        self.addr_to_set_freq_csr = CSRStorage(WIDTH_32_BITS, description="The freq of the row to attack in the DRAM")
        self.addr_to_set_val_out_csr = CSRStorage(rw_test_port.address_width, description="The row to attack in the DRAM, output")
        self.addr_to_set_freq_out_csr = CSRStorage(WIDTH_32_BITS, description="The freq of the row to attack in the DRAM, output")
        self.addr_to_set_total_addrs_csr = CSRStorage(rw_test_port.address_width, description="Set the total number of rows desired to attack (ex. 1 - 20)")
        self.addr_to_set_ack_csr = CSRStatus(ONE_BIT_WIDE, description="Next sig acknowledged")



        """
        Signals
        """

        ###########################################################################
        # Bits and their frequencies
        ###########################################################################

        # First 10 bits, changeable frequencies
        addr_1_val_sig = Signal(rw_test_port.address_width)
        addr_1_freq_sig = Signal(WIDTH_32_BITS)
        addr_2_val_sig = Signal(rw_test_port.address_width)
        addr_2_freq_sig = Signal(WIDTH_32_BITS)
        addr_3_val_sig = Signal(rw_test_port.address_width)
        addr_3_freq_sig = Signal(WIDTH_32_BITS)
        addr_4_val_sig = Signal(rw_test_port.address_width)
        addr_4_freq_sig = Signal(WIDTH_32_BITS)
        addr_5_val_sig = Signal(rw_test_port.address_width)
        addr_5_freq_sig = Signal(WIDTH_32_BITS)
        addr_6_val_sig = Signal(rw_test_port.address_width)
        addr_6_freq_sig = Signal(WIDTH_32_BITS)
        addr_7_val_sig = Signal(rw_test_port.address_width)
        addr_7_freq_sig = Signal(WIDTH_32_BITS)
        addr_8_val_sig = Signal(rw_test_port.address_width)
        addr_8_freq_sig = Signal(WIDTH_32_BITS)
        addr_9_val_sig = Signal(rw_test_port.address_width)
        addr_9_freq_sig = Signal(WIDTH_32_BITS)
        addr_10_val_sig = Signal(rw_test_port.address_width)
        addr_10_freq_sig = Signal(WIDTH_32_BITS)

        # Second 10, all have freq of one
        addr_11_val_sig = Signal(rw_test_port.address_width)
        addr_12_val_sig = Signal(rw_test_port.address_width)
        addr_13_val_sig = Signal(rw_test_port.address_width)
        addr_14_val_sig = Signal(rw_test_port.address_width)
        addr_15_val_sig = Signal(rw_test_port.address_width)
        addr_16_val_sig = Signal(rw_test_port.address_width)
        addr_17_val_sig = Signal(rw_test_port.address_width)
        addr_18_val_sig = Signal(rw_test_port.address_width)
        addr_19_val_sig = Signal(rw_test_port.address_width)
        addr_20_val_sig = Signal(rw_test_port.address_width)

        ###########################################################################

        """
        Addr and Freq Set Sync Block
        """

        self.sync += [

        ]



        """
        Row Hammer FSM
        """

        rh_fsm = FSM(reset_state="RH_IDLE")
        self.submodules.rh_fsm = rh_fsm

        rh_fsm.act("RH_IDLE")
        rh_fsm.act("RH_FILL_REQ")
        rh_fsm.act("RH_FILL_REQ_REC")
        rh_fsm.act("RH_FILL_REC")
        rh_fsm.act("RH_INIT_CHECK")
        rh_fsm.act("RH_INIT_SETTINGS")
        rh_fsm.act("RH_BIT_REQ")
        rh_fsm.act("RH_BIT_REQ_REC")
        rh_fsm.act("RH_BIT_REC")
        rh_fsm.act("RH_RESET_SETTINGS")
        rh_fsm.act("RH_FINAL_CHECK")





        """
        Read control FSM
        """

        read_ctrl_fsm = FSM(reset_state="READ_IDLE")
        self.submodules.read_ctrl_fsm = read_ctrl_fsm

        read_ctrl_fsm.act("READ_IDLE")
        read_ctrl_fsm.act("READ_CHECK_REQ")
        read_ctrl_fsm.act("READ_CHECK_REQ_REC")
        read_ctrl_fsm.act("READ_CHECK_REC")
        read_ctrl_fsm.act("READ_CHECK_ERR_REQ")
        read_ctrl_fsm.act("READ_CHECK_ERR_REC")
        read_ctrl_fsm.act("READ_CHECK_ERR_DISPLAY")
        read_ctrl_fsm.act("READ_FINISH")



        