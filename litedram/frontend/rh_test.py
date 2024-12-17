"""
A self-made implementation of a rowhammer-test state machine.
"""


from migen import *

from litex.soc.interconnect.csr import *

from litedram.common import LiteDRAMNativePort



"""
Constants
"""

# Signal width constants
ONE_BIT_WIDE = 1
TWO_BITS_WIDE = 2
WIDTH_8_BITS = 8
WIDTH_16_BITS = 16
WIDTH_32_BITS = 32
WIDTH_64_BITS = 64

# Timer Value Constants
ADDR_FREQ_SET_DELAY = 10000
DATA_SET_DELAY = 10000
ROWHAMER_DELAY = 10000

# Set Addr Freq Cntrl Constants
SET_ADDR_1_CONST = 0
SET_ADDR_2_CONST = 1
SET_ADDR_3_CONST = 2
SET_ADDR_4_CONST = 3
SET_ADDR_5_CONST = 4
SET_ADDR_6_CONST = 5
SET_ADDR_7_CONST = 6
SET_ADDR_8_CONST = 7
SET_ADDR_9_CONST = 8
SET_ADDR_10_CONST = 9
SET_ADDR_11_CONST = 10
SET_ADDR_12_CONST = 11
SET_ADDR_13_CONST = 12
SET_ADDR_14_CONST = 13
SET_ADDR_15_CONST = 14
SET_ADDR_16_CONST = 15
SET_ADDR_17_CONST = 16
SET_ADDR_18_CONST = 17
SET_ADDR_19_CONST = 18
SET_ADDR_20_CONST = 19
SET_NUM_ADDRS_CONST = 20

# Feedback State Sections
RH_IDLE_STATE = 0x100
RH_WRITE_FILL_INIT_STATE = 0x200
RH_READ_CHECK_STATE = 0x400
RH_READ_SEND_ERRORS_STATE = 0x800
RH_INIT_SETTINGS_STATE = 0x1000
RH_ROWHAMMER_STATE = 0x2000
RH_RESET_SETTNGS_STATE = 0x4000
RH_FINAL_CHECK = 0x8000

# Feedback State Values
RH_FIRST_STATE = 0x0
RH_SECOND_STATE = 0x1
RH_THIRD_STATE = 0x2
RH_FOURTH_STATE = 0x3
RH_FIFTH_STATE = 0x4
RH_SIXTH_STATE = 0x5
RH_SEVENTH_STATE = 0x6
RH_EIGHTH_STATE = 0x7
RH_NINTH_STATE = 0x8
RH_TENTH_STATE = 0x9
RH_ELEVENTH_STATE = 0xa
RH_TWELFTH_STATE = 0xb
RH_THIRTEENTH_STATE = 0xc
RH_FOURTEENTH_STATE = 0xd
RH_FIFTEENTH_STATE = 0xe
RH_SIXTEENTH_STATE = 0xf
RH_SEVENTEENTH_STATE = 0x10
RH_EIGHTEENTH_STATE = 0x11
RH_NINETEENTH_STATE = 0x12
RH_TWENTIETH_STATE = 0x13


class Row_Hammer_Test(Module, AutoCSR):

    def __init__(self, rw_test_port : LiteDRAMNativePort, sys_clk_freq : int, trefi : Signal, refresh_enable : Signal, auto_precharge_setting : Signal, bank_bits, col_bits, trefi_setting):

        self.rw_test_port = rw_test_port

        # Address width integers
        PORT_COLS_AND_BANKS_PER_ROW_ADDR = 2 ** (bank_bits + col_bits) 

        """
        CSR Registers
        """

        # Control the number of rows and the frequency of attacking them - Control CSR registers
        self.addr_to_set_val_csr = CSRStorage(rw_test_port.address_width, description="The row to attack in the DRAM")
        self.addr_to_set_freq_csr = CSRStorage(WIDTH_32_BITS, description="The freq of the row to attack in the DRAM")
        self.addr_to_set_val_out_csr = CSRStatus(rw_test_port.address_width, description="The row to attack in the DRAM, output")
        self.addr_to_set_freq_out_csr = CSRStatus(WIDTH_32_BITS, description="The freq of the row to attack in the DRAM, output")
        self.addr_to_set_sel_val_csr = CSRStorage(WIDTH_32_BITS, description="Select the value of the row to set")
        self.addr_to_set_start_fsm_csr = CSRStorage(ONE_BIT_WIDE, description="Start setting addr and freq fsm")
        self.addr_to_set_set_not_get_csr = CSRStorage(ONE_BIT_WIDE, description="High: set the val and freq, Low: get the val and freq for display")
        self.addr_to_set_start_prev_csr = CSRStatus(ONE_BIT_WIDE, description="One bit signal, high once start pulse has run")

        # Input data CSR registers
        self.input_data_set_not_get_csr = CSRStorage(ONE_BIT_WIDE, description="High: set the data, Low: get the data for display")
        self.input_data_sel_val_csr = CSRStorage(WIDTH_32_BITS, description="Select where to put data (0 for even addresses, 1 for odd)")
        self.input_data_double_pattern_setting_csr = CSRStorage(ONE_BIT_WIDE, description="Use a double data pattern, 0 for disable")
        self.input_data_pattern_csr = CSRStorage(WIDTH_32_BITS, description="Data pattern written to DRAM (Replicated/Concatenated to fill DRAM data width)")
        self.input_data_pattern_output_csr = CSRStatus(WIDTH_32_BITS, description="Output the data pattern we want to see")
        self.input_data_to_set_start_fsm_csr = CSRStorage(ONE_BIT_WIDE, description="Start setting data fsm")
        self.input_data_set_start_prev_csr = CSRStatus(ONE_BIT_WIDE, description="One bit signal, high once start pulse has run")
        self.data_width_csr = CSRStatus(WIDTH_32_BITS, reset=rw_test_port.data_width, description="The width of the data for reference")

        # Change refresh rate, or enable it
        self.refresh_enable_csr = CSRStorage(ONE_BIT_WIDE, reset=1, description="Enable DRAM refresh for test")
        self.refresh_rate_csr = CSRStorage(WIDTH_32_BITS, reset=trefi_setting, description="Choose refresh rate")

        # Change auto refresh setting
        self.auto_precharge_csr = CSRStorage(1, description="Enable or Disable auto csr refresh for row hammer test")

        # Address sig csr
        self.address_csr = CSRStatus(rw_test_port.address_width, description="Control address while making it available to user")
        
        # Output data CSR registers
        self.output_data_pattern1_csr = CSRStatus(WIDTH_32_BITS, description="Data read after performing read")
        self.output_data_pattern2_csr = CSRStatus(WIDTH_32_BITS, description="Data read after performing read")
        self.output_data_pattern3_csr = CSRStatus(WIDTH_32_BITS, description="Data read after performing read")
        self.output_data_pattern4_csr = CSRStatus(WIDTH_32_BITS, description="Data read after performing read")
        self.output_data_pattern5_csr = CSRStatus(WIDTH_32_BITS, description="Data read after performing read")
        self.output_data_pattern6_csr = CSRStatus(WIDTH_32_BITS, description="Data read after performing read")
        self.output_data_pattern7_csr = CSRStatus(WIDTH_32_BITS, description="Data read after performing read")
        self.output_data_pattern8_csr = CSRStatus(WIDTH_32_BITS, description="Data read after performing read")
        self.output_data_pattern9_csr = CSRStatus(WIDTH_32_BITS, description="Data read after performing read")
        self.output_data_pattern10_csr = CSRStatus(WIDTH_32_BITS, description="Data read after performing read")
        self.output_data_pattern11_csr = CSRStatus(WIDTH_32_BITS, description="Data read after performing read")
        self.output_data_pattern12_csr = CSRStatus(WIDTH_32_BITS, description="Data read after performing read")
        self.output_data_pattern13_csr = CSRStatus(WIDTH_32_BITS, description="Data read after performing read")
        self.output_data_pattern14_csr = CSRStatus(WIDTH_32_BITS, description="Data read after performing read")
        self.output_data_pattern15_csr = CSRStatus(WIDTH_32_BITS, description="Data read after performing read")
        self.output_data_pattern16_csr = CSRStatus(WIDTH_32_BITS, description="Data read after performing read")
        self.output_data_pattern17_csr = CSRStatus(WIDTH_32_BITS, description="Data read after performing read")
        self.output_data_pattern18_csr = CSRStatus(WIDTH_32_BITS, description="Data read after performing read")

        # Rowhammer Tester FSM CSR registers
        self.rowhammer_start_fsm_csr = CSRStorage(ONE_BIT_WIDE, description="Start the Rowhammer tester")
        self.rowhammer_start_prev_fsm_csr = CSRStatus(ONE_BIT_WIDE, description="Keep track of previous value of start")
        self.rowhammer_err_cnt_csr = CSRStatus(WIDTH_32_BITS, description="Count the total errors before/after rowhammer test")
        # Useful for debugging if needed, replace with num_addrs_attack_sig signal
        # self.rowhammer_state_counter_csr = CSRStorage(WIDTH_32_BITS, description="Store the number of addresses as an option (up to 9)")
        self.rowhammer_state_cycle_counter_csr = CSRStorage(WIDTH_32_BITS, reset=1, description="Store the number of cycles as an option")
        self.rowhammer_state_cycle_counter_val_output_csr = CSRStatus(WIDTH_32_BITS, reset=1, description="Show the number of cycles")

        # # Read FSM CSR registers
        # self.read_fsm_paused_csr = CSRStatus(ONE_BIT_WIDE, description="Goes high when finished a read cycle, must be acknowledged")
        # self.read_fsm_ack_csr = CSRStorage(ONE_BIT_WIDE, description="Acknowledge that the read state machine has paused, can continue")

        # Error acknowledging for displaying errors
        self.error_ack_csr = CSRStorage(ONE_BIT_WIDE, description="Acknowledge error has been sent")
        self.error_ack_prev_csr = CSRStatus(ONE_BIT_WIDE, description="See that error signal has been seen and received")
        self.error_found_flag_csr = CSRStatus(ONE_BIT_WIDE, description="High if the state machine is paused, as an error has been found.")

        # CSR register for giving back feedback to user of where we are
        self.feedback_state_csr = CSRStatus(WIDTH_16_BITS, description="Feedback of which state the fsm is in")

        # Obtain address width, bank bits, column bits
        self.address_width_csr = CSRStatus(WIDTH_8_BITS, reset=rw_test_port.address_width, description="Holds address width value")
        self.bank_width_csr = CSRStatus(WIDTH_8_BITS, reset=bank_bits, description="Holds bank width value")
        self.col_width_csr = CSRStatus(WIDTH_8_BITS, reset=col_bits, description="Holds column width value")

        # Reader fsm guider signal, Guide for state machine: running reader before or after rh test
        self.before_after_rh_csr = CSRStatus(ONE_BIT_WIDE, description="Controls return state after reader is finished")

        """
        Signals
        """

        # Address sigs
        max_address_sig = Signal(rw_test_port.address_width)
        self.burst_cntr_sig = Signal(WIDTH_32_BITS) # Important signal, counts the number 
                                               # reads/writes, knows when to finish fsm.

        # Data sigs for switching pattern
        data_sig_1 = Signal(rw_test_port.data_width)
        data_sig_2 = Signal(rw_test_port.data_width)
        data_sig_timer = Signal(rw_test_port.data_width)
        error_data = Signal(rw_test_port.data_width)

        ###########################################################################
        # Addrs and freq sigs
        ###########################################################################

        # First 10 addrs, changeable frequencies
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

        # Store the number of addrs to attack
        num_addrs_attack_sig = Signal(WIDTH_32_BITS)

        # Control addr, freq setting signals
        addr_freq_set_start_buf1_sig = Signal(ONE_BIT_WIDE)
        addr_freq_set_start_buf2_sig = Signal(ONE_BIT_WIDE)
        addr_freq_set_start_sig = Signal(ONE_BIT_WIDE)
        addr_freq_set_timer = Signal(WIDTH_32_BITS)

        # Control data setting signals
        self.data_set_start_buf1_sig = data_set_start_buf1_sig = Signal(ONE_BIT_WIDE)
        self.data_set_start_buf2_sig = data_set_start_buf2_sig = Signal(ONE_BIT_WIDE)
        self.data_set_start_sig = data_set_start_sig = Signal(ONE_BIT_WIDE)
        self.data_set_timer = data_set_timer = Signal(WIDTH_32_BITS)

        # Error acknowledging and oneshot signals
        error_ack_sig = Signal(ONE_BIT_WIDE)
        error_ack_buf1_sig = Signal(ONE_BIT_WIDE)
        error_ack_buf2_sig = Signal(ONE_BIT_WIDE)

        # Rowhammer attack timer, Keep track of frequencies of attacked addresses
        self.rowhammer_attack_cmd_timer_sig = rowhammer_attack_cmd_timer_sig = Signal(WIDTH_32_BITS)

        # Flip the type of data we write
        input_data_double_pattern_setting = Signal(ONE_BIT_WIDE)

        ###########################################################################

        ###########################################################################
        # Rowhammer FSM sigs
        ###########################################################################

        rowhammer_start_buf1_sig = Signal(ONE_BIT_WIDE)
        rowhammer_start_buf2_sig = Signal(ONE_BIT_WIDE)
        rowhammer_start_sig = Signal(ONE_BIT_WIDE)
        self.rowhammer_two_states_counter_1_storage_sig = rowhammer_two_states_counter_1_storage_sig = Signal(WIDTH_32_BITS, reset=1)
        self.rowhammer_two_states_counter_2_storage_sig = rowhammer_two_states_counter_2_storage_sig = Signal(WIDTH_32_BITS, reset=1)
        self.rowhammer_two_states_counter_3_storage_sig = rowhammer_two_states_counter_3_storage_sig = Signal(WIDTH_32_BITS, reset=1)
        self.rowhammer_two_states_counter_4_storage_sig = rowhammer_two_states_counter_4_storage_sig = Signal(WIDTH_32_BITS, reset=1)
        self.rowhammer_two_states_counter_5_storage_sig = rowhammer_two_states_counter_5_storage_sig = Signal(WIDTH_32_BITS, reset=1)
        self.temporary_state_machine_var = Signal(ONE_BIT_WIDE)
        self.rowhammer_two_states_counter_sig = rowhammer_two_states_counter_sig = Signal(WIDTH_32_BITS)
        self.rowhammer_state_cycle_counter = rowhammer_state_cycle_counter = Signal(WIDTH_32_BITS)
        self.rowhammer_state_cycle_storage_counter = rowhammer_state_cycle_storage_counter = Signal(WIDTH_32_BITS, reset=1)
        self.rowhammer_state_counter = rowhammer_state_counter = Signal(WIDTH_32_BITS)
        rowhammer_port_wready_rvalid_counter = Signal(WIDTH_32_BITS)

        ###########################################################################

        """
        Addr and freq set FSM
        """

        addr_and_freq_fsm = FSM(reset_state="SET_FREQ_ADDR_IDLE")
        self.submodules.addr_and_freq_fsm = addr_and_freq_fsm

        addr_and_freq_fsm.act("SET_FREQ_ADDR_IDLE",
            If(addr_freq_set_start_sig,
                NextState("SET_FREQ_ADDR_SET_VAL"),
            ).Else(
                NextState("SET_FREQ_ADDR_IDLE"),
            )              
        )


        # My idea for incrementing addresses: Make an incrementing signal, controlling
        # both the amount each address cah increment, and the limit of the times it can increment. 
        addr_and_freq_fsm.act("SET_FREQ_ADDR_SET_VAL",
            If(self.addr_to_set_set_not_get_csr.storage,
                If(self.addr_to_set_sel_val_csr.storage == SET_ADDR_1_CONST,
                    NextValue(addr_1_val_sig, self.addr_to_set_val_csr.storage),
                    NextValue(addr_1_freq_sig, self.addr_to_set_freq_csr.storage),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_2_CONST,
                    NextValue(addr_2_val_sig, self.addr_to_set_val_csr.storage),
                    NextValue(addr_2_freq_sig, self.addr_to_set_freq_csr.storage),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_3_CONST,
                    NextValue(addr_3_val_sig, self.addr_to_set_val_csr.storage),
                    NextValue(addr_3_freq_sig, self.addr_to_set_freq_csr.storage),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_4_CONST,
                    NextValue(addr_4_val_sig, self.addr_to_set_val_csr.storage),
                    NextValue(addr_4_freq_sig, self.addr_to_set_freq_csr.storage),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_5_CONST,
                    NextValue(addr_5_val_sig, self.addr_to_set_val_csr.storage),
                    NextValue(addr_5_freq_sig, self.addr_to_set_freq_csr.storage),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_6_CONST,
                    NextValue(addr_6_val_sig, self.addr_to_set_val_csr.storage),
                    NextValue(addr_6_freq_sig, self.addr_to_set_freq_csr.storage),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_7_CONST,
                    NextValue(addr_7_val_sig, self.addr_to_set_val_csr.storage),
                    NextValue(addr_7_freq_sig, self.addr_to_set_freq_csr.storage),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_8_CONST,
                    NextValue(addr_8_val_sig, self.addr_to_set_val_csr.storage),
                    NextValue(addr_8_freq_sig, self.addr_to_set_freq_csr.storage),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_9_CONST,
                    NextValue(addr_9_val_sig, self.addr_to_set_val_csr.storage),
                    NextValue(addr_9_freq_sig, self.addr_to_set_freq_csr.storage),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_10_CONST,
                    NextValue(addr_10_val_sig, self.addr_to_set_val_csr.storage),
                    NextValue(addr_10_freq_sig, self.addr_to_set_freq_csr.storage),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_11_CONST,
                    NextValue(addr_11_val_sig, self.addr_to_set_val_csr.storage),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_12_CONST,
                    NextValue(addr_12_val_sig, self.addr_to_set_val_csr.storage),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_13_CONST,
                    NextValue(addr_13_val_sig, self.addr_to_set_val_csr.storage),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_14_CONST,
                    NextValue(addr_14_val_sig, self.addr_to_set_val_csr.storage),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_15_CONST,
                    NextValue(addr_15_val_sig, self.addr_to_set_val_csr.storage),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_16_CONST,
                    NextValue(addr_16_val_sig, self.addr_to_set_val_csr.storage),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_17_CONST,
                    NextValue(addr_17_val_sig, self.addr_to_set_val_csr.storage),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_18_CONST,
                    NextValue(addr_18_val_sig, self.addr_to_set_val_csr.storage),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_19_CONST,
                    NextValue(addr_19_val_sig, self.addr_to_set_val_csr.storage),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_20_CONST,
                    NextValue(addr_20_val_sig, self.addr_to_set_val_csr.storage),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_NUM_ADDRS_CONST,
                    NextValue(num_addrs_attack_sig, self.addr_to_set_freq_csr.storage),       
                ),
            ).Else(
                If(self.addr_to_set_sel_val_csr.storage == SET_ADDR_1_CONST,
                    NextValue(self.addr_to_set_val_out_csr.status, addr_1_val_sig),
                    NextValue(self.addr_to_set_freq_out_csr.status, addr_1_freq_sig),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_2_CONST,
                    NextValue(self.addr_to_set_val_out_csr.status, addr_2_val_sig),
                    NextValue(self.addr_to_set_freq_out_csr.status, addr_2_freq_sig),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_3_CONST,
                    NextValue(self.addr_to_set_val_out_csr.status, addr_3_val_sig),
                    NextValue(self.addr_to_set_freq_out_csr.status, addr_3_freq_sig),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_4_CONST,
                    NextValue(self.addr_to_set_val_out_csr.status, addr_4_val_sig),
                    NextValue(self.addr_to_set_freq_out_csr.status, addr_4_freq_sig),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_5_CONST,
                    NextValue(self.addr_to_set_val_out_csr.status, addr_5_val_sig),
                    NextValue(self.addr_to_set_freq_out_csr.status, addr_5_freq_sig),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_6_CONST,
                    NextValue(self.addr_to_set_val_out_csr.status, addr_6_val_sig),
                    NextValue(self.addr_to_set_freq_out_csr.status, addr_6_freq_sig),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_7_CONST,
                    NextValue(self.addr_to_set_val_out_csr.status, addr_7_val_sig),
                    NextValue(self.addr_to_set_freq_out_csr.status, addr_7_freq_sig),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_8_CONST,
                    NextValue(self.addr_to_set_val_out_csr.status, addr_8_val_sig),
                    NextValue(self.addr_to_set_freq_out_csr.status, addr_8_freq_sig),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_9_CONST,
                    NextValue(self.addr_to_set_val_out_csr.status, addr_9_val_sig),
                    NextValue(self.addr_to_set_freq_out_csr.status, addr_9_freq_sig),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_10_CONST,
                    NextValue(self.addr_to_set_val_out_csr.status, addr_10_val_sig),
                    NextValue(self.addr_to_set_freq_out_csr.status, addr_10_freq_sig),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_11_CONST,
                    NextValue(self.addr_to_set_val_out_csr.status, addr_11_val_sig),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_12_CONST,
                    NextValue(self.addr_to_set_val_out_csr.status, addr_12_val_sig),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_13_CONST,
                    NextValue(self.addr_to_set_val_out_csr.status, addr_13_val_sig),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_14_CONST,
                    NextValue(self.addr_to_set_val_out_csr.status, addr_14_val_sig),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_15_CONST,
                    NextValue(self.addr_to_set_val_out_csr.status, addr_15_val_sig),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_16_CONST,
                    NextValue(self.addr_to_set_val_out_csr.status, addr_16_val_sig),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_17_CONST,
                    NextValue(self.addr_to_set_val_out_csr.status, addr_17_val_sig),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_18_CONST,
                    NextValue(self.addr_to_set_val_out_csr.status, addr_18_val_sig),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_19_CONST,
                    NextValue(self.addr_to_set_val_out_csr.status, addr_19_val_sig),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_ADDR_20_CONST,
                    NextValue(self.addr_to_set_val_out_csr.status, addr_20_val_sig),
                ).Elif(self.addr_to_set_sel_val_csr.storage == SET_NUM_ADDRS_CONST,
                    NextValue(self.addr_to_set_freq_out_csr.status, num_addrs_attack_sig),       
                ),
            ),
            NextState("SET_FREQ_ADDR_IDLE"),
        )



        """
        Addr and freq set sync block
        """
        self.sync += [

            # Buffered Input
            addr_freq_set_start_buf1_sig.eq(self.addr_to_set_start_fsm_csr.storage),
            addr_freq_set_start_buf2_sig.eq(addr_freq_set_start_buf1_sig),

            # Oneshot and Timer
            If(addr_freq_set_start_buf2_sig,
                If(addr_freq_set_timer < ADDR_FREQ_SET_DELAY,
                    addr_freq_set_timer.eq(addr_freq_set_timer + 1),
                ).Else(
                    If(self.addr_to_set_start_prev_csr.status,
                        addr_freq_set_start_sig.eq(0),
                        self.addr_to_set_start_prev_csr.status.eq(1),
                    ).Else(
                        addr_freq_set_start_sig.eq(1),
                        self.addr_to_set_start_prev_csr.status.eq(1),
                    )
                )
            ).Else(
                addr_freq_set_timer.eq(0),
                addr_freq_set_start_sig.eq(0),
                self.addr_to_set_start_prev_csr.status.eq(0),
            )
        ]



        # ##############################################################################################


        """
        data and timer set FSM
        """

        data_fsm = FSM(reset_state="SET_DATA_IDLE")
        self.submodules.data_fsm = data_fsm

        data_fsm.act("SET_DATA_IDLE",
            self.temporary_state_machine_var.eq(0),
            If(data_set_start_sig,
                NextState("SET_DATA_SET_VAL"),
            ).Else(
                NextState("SET_DATA_IDLE"),
            )              
        )

        data_fsm.act("SET_DATA_SET_VAL",
            self.temporary_state_machine_var.eq(1),
            If(self.input_data_set_not_get_csr.storage,
                If(self.input_data_sel_val_csr.storage == SET_ADDR_1_CONST,
                    NextValue(data_sig_1, Replicate(self.input_data_pattern_csr.storage, rw_test_port.data_width // len(self.input_data_pattern_csr.storage))),  
                ).Elif(self.input_data_sel_val_csr.storage == SET_ADDR_2_CONST,
                    NextValue(data_sig_2, Replicate(self.input_data_pattern_csr.storage, rw_test_port.data_width // len(self.input_data_pattern_csr.storage))), 
                ).Elif(self.input_data_sel_val_csr.storage == SET_ADDR_3_CONST,
                    NextValue(rowhammer_two_states_counter_1_storage_sig, self.rowhammer_state_cycle_counter_csr.storage)       
                ).Elif(self.input_data_sel_val_csr.storage == SET_ADDR_4_CONST,
                    NextValue(rowhammer_two_states_counter_2_storage_sig, self.rowhammer_state_cycle_counter_csr.storage)       
                ).Elif(self.input_data_sel_val_csr.storage == SET_ADDR_5_CONST,
                    NextValue(rowhammer_two_states_counter_3_storage_sig, self.rowhammer_state_cycle_counter_csr.storage)       
                ).Elif(self.input_data_sel_val_csr.storage == SET_ADDR_6_CONST,
                    NextValue(rowhammer_two_states_counter_4_storage_sig, self.rowhammer_state_cycle_counter_csr.storage)       
                ).Elif(self.input_data_sel_val_csr.storage == SET_ADDR_7_CONST,
                    NextValue(rowhammer_two_states_counter_5_storage_sig, self.rowhammer_state_cycle_counter_csr.storage)       
                ).Elif(self.input_data_sel_val_csr.storage == SET_ADDR_8_CONST,
                    NextValue(rowhammer_state_cycle_storage_counter, self.rowhammer_state_cycle_counter_csr.storage)       
                )
            ).Else(
                If(self.input_data_sel_val_csr.storage == SET_ADDR_1_CONST,
                    NextValue(self.input_data_pattern_output_csr.status, data_sig_1[0:WIDTH_32_BITS]), 
                ).Elif(self.input_data_sel_val_csr.storage == SET_ADDR_2_CONST,
                    NextValue(self.input_data_pattern_output_csr.status, data_sig_2[0:WIDTH_32_BITS]),
                ).Elif(self.input_data_sel_val_csr.storage == SET_ADDR_3_CONST,
                    NextValue(self.rowhammer_state_cycle_counter_val_output_csr.status, rowhammer_two_states_counter_1_storage_sig),
                ).Elif(self.input_data_sel_val_csr.storage == SET_ADDR_4_CONST,
                    NextValue(self.rowhammer_state_cycle_counter_val_output_csr.status, rowhammer_two_states_counter_2_storage_sig),
                ).Elif(self.input_data_sel_val_csr.storage == SET_ADDR_5_CONST,
                    NextValue(self.rowhammer_state_cycle_counter_val_output_csr.status, rowhammer_two_states_counter_3_storage_sig),
                ).Elif(self.input_data_sel_val_csr.storage == SET_ADDR_6_CONST,
                    NextValue(self.rowhammer_state_cycle_counter_val_output_csr.status, rowhammer_two_states_counter_4_storage_sig),
                ).Elif(self.input_data_sel_val_csr.storage == SET_ADDR_7_CONST,
                    NextValue(self.rowhammer_state_cycle_counter_val_output_csr.status, rowhammer_two_states_counter_5_storage_sig),
                ).Elif(self.input_data_sel_val_csr.storage == SET_ADDR_8_CONST,
                    NextValue(self.rowhammer_state_cycle_counter_val_output_csr.status, rowhammer_state_cycle_storage_counter),
                )
            ),
            NextState("SET_DATA_IDLE"),
        )

        """
        data and timer set sync block
        """
        self.sync += [

            # Buffered Input
            data_set_start_buf1_sig.eq(self.input_data_to_set_start_fsm_csr.storage),
            data_set_start_buf2_sig.eq(data_set_start_buf1_sig),

            If(data_set_start_buf2_sig,
                If(data_set_timer < DATA_SET_DELAY,
                    data_set_timer.eq(data_set_timer + 1),
                ).Else(
                    If(self.input_data_set_start_prev_csr.status,
                        data_set_start_sig.eq(0),
                        self.input_data_set_start_prev_csr.status.eq(1),
                    ).Else(
                        data_set_start_sig.eq(1),
                        self.input_data_set_start_prev_csr.status.eq(1),
                    )
                )
            ).Else(
                data_set_start_sig.eq(0),
                If(data_set_timer > 0,
                    self.input_data_set_start_prev_csr.status.eq(1),
                    data_set_timer.eq(data_set_timer - 1)
                ).Else(
                    self.input_data_set_start_prev_csr.status.eq(0),
                )
            )
            
        ]



        """
        Row Hammer FSM
        """

        rh_fsm = FSM(reset_state="RH_IDLE")
        self.submodules.rh_fsm = rh_fsm

        # Idle state, wait here until user turns on row hammer tester
        rh_fsm.act("RH_IDLE",
            self.feedback_state_csr.status.eq(RH_IDLE_STATE),
            If(rowhammer_start_sig,
                NextValue(self.address_csr.status, 0),
                NextValue(input_data_double_pattern_setting, 0),
                # NextValue(rw_test_port.wdata.data, data_sig[0:rw_test_port.data_width]),
                NextValue(rw_test_port.wdata.data, data_sig_1),
                NextValue(data_sig_timer, PORT_COLS_AND_BANKS_PER_ROW_ADDR),
                NextState("RH_FILL_REQ"),
            ).Else(
                NextState("RH_IDLE"), 
            ) 
        )

        # Beginning of sending commands to write designated data pattern 
        # to entire DRAM. Once we get the OK (cmd.ready), move on to 
        # the next state of both sending commands and counting received ones.
        rh_fsm.act("RH_FILL_REQ",
            self.feedback_state_csr.status.eq(RH_WRITE_FILL_INIT_STATE | RH_FIRST_STATE),
            rw_test_port.cmd.we.eq(1),
            rw_test_port.cmd.valid.eq(1),
            If(rw_test_port.cmd.ready,
                If(self.address_csr.status == max_address_sig,
                    NextValue(self.address_csr.status, 0),
                    NextValue(self.burst_cntr_sig, 0),
                    NextState("RH_FILL_REC"),   
                ).Else(
                    NextValue(data_sig_timer, data_sig_timer - 1),
                    NextValue(self.address_csr.status, self.address_csr.status + 1),
                    NextValue(self.burst_cntr_sig, 0),
                    If(self.input_data_double_pattern_setting_csr.storage & input_data_double_pattern_setting,
                        NextValue(rw_test_port.wdata.data, data_sig_2),
                    ),
                    NextState("RH_FILL_REQ_REC"),
                )
            )
        )

        # Send commands, count both the number received and the number 
        # number executed, wait till we reach the very last address
        rh_fsm.act("RH_FILL_REQ_REC",
            self.feedback_state_csr.status.eq(RH_WRITE_FILL_INIT_STATE | RH_SECOND_STATE),
            rw_test_port.cmd.we.eq(1),
            rw_test_port.wdata.valid.eq(1),
            rw_test_port.cmd.valid.eq(1),
            If(rw_test_port.wdata.ready,
                If(self.input_data_double_pattern_setting_csr.storage & input_data_double_pattern_setting,
                    NextValue(rw_test_port.wdata.data, data_sig_2),
                ).Else(
                    NextValue(rw_test_port.wdata.data, data_sig_1),
                ),
                If((data_sig_timer - 1) == 0,
                    NextValue(input_data_double_pattern_setting, ~input_data_double_pattern_setting),
                    NextValue(data_sig_timer, PORT_COLS_AND_BANKS_PER_ROW_ADDR),
                ).Else(
                    NextValue(data_sig_timer, data_sig_timer - 1),
                ),
                NextValue(self.burst_cntr_sig, self.burst_cntr_sig + 1),  
            ),
            If(rw_test_port.cmd.ready,
                If(self.address_csr.status == max_address_sig,
                    NextValue(self.address_csr.status, 0),
                    NextState("RH_FILL_REC")
                ).Else(
                    NextValue(self.address_csr.status, self.address_csr.status + 1),
                )
            )
        )

        # Keep receiving commands till we finish
        rh_fsm.act("RH_FILL_REC",
            self.feedback_state_csr.status.eq(RH_WRITE_FILL_INIT_STATE | RH_THIRD_STATE),
            rw_test_port.cmd.we.eq(1),
            rw_test_port.wdata.valid.eq(1),
            If(rw_test_port.wdata.ready,
                If(self.input_data_double_pattern_setting_csr.storage & input_data_double_pattern_setting,
                    NextValue(rw_test_port.wdata.data, data_sig_2),
                ).Else(
                    NextValue(rw_test_port.wdata.data, data_sig_1),
                ),
                If((data_sig_timer - 1) == 0,
                    NextValue(input_data_double_pattern_setting, ~input_data_double_pattern_setting),
                    NextValue(data_sig_timer, PORT_COLS_AND_BANKS_PER_ROW_ADDR),
                ).Else(
                    NextValue(data_sig_timer, data_sig_timer - 1),
                ),
                NextValue(self.burst_cntr_sig, self.burst_cntr_sig + 1),
                If((self.burst_cntr_sig + 1) >= (max_address_sig + 1),
                    NextValue(self.burst_cntr_sig, 0),
                    NextValue(self.address_csr.status, 0),
                    NextValue(self.rowhammer_err_cnt_csr.status, 0),
                    NextValue(self.before_after_rh_csr.status, 0),
                    NextValue(input_data_double_pattern_setting, 0),
                    NextValue(data_sig_timer, PORT_COLS_AND_BANKS_PER_ROW_ADDR),
                    NextState("READ_CHECK_REQ"),
                )
            )
        )

        # Initial settings for the row hammer attack
        rh_fsm.act("RH_INIT_SETTINGS",
            # Modify refresh rate here
            self.feedback_state_csr.status.eq(RH_INIT_SETTINGS_STATE),
            NextState("RH_ATTACK_1"),
            If(self.refresh_enable_csr.storage,
                NextValue(trefi, self.refresh_rate_csr.storage),
            ).Else(
                NextValue(refresh_enable, 0),
            ),
            NextValue(auto_precharge_setting, self.auto_precharge_csr.storage),
            NextValue(self.address_csr.status, addr_1_val_sig),
            NextValue(rowhammer_attack_cmd_timer_sig, addr_1_freq_sig),
            NextValue(rowhammer_state_counter, num_addrs_attack_sig),
            NextValue(rowhammer_state_cycle_counter, rowhammer_state_cycle_storage_counter),
            NextValue(rowhammer_port_wready_rvalid_counter, 0),
            NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_1_storage_sig),
        )

        # First row hammer attack state
        rh_fsm.act("RH_ATTACK_1",
            self.feedback_state_csr.status.eq(RH_ROWHAMMER_STATE | RH_FIRST_STATE),
                   
            # Set command valid
            rw_test_port.cmd.valid.eq(1),

            # Control necessary signals for reads
            rw_test_port.cmd.we.eq(0),
            rw_test_port.rdata.ready.eq(1),

            # Control if we need to quit or move on to next bit after command execution
            If(rw_test_port.cmd.ready,
                
                # A timer containing the number of times to hammer the bit (addr_#_freq_sig)
                # Once it finishes, we go to a next state (RH_RESET_SETTINGS, RH_ATTACK_1, RH_ATTACK_2)
                If((rowhammer_attack_cmd_timer_sig - 1) == 0,
                    
                    # A timer controlling whether to 1. continue the cycle of states, or 
                    # 2. repeat the cycle of states (go back to the first state) or finish.
                    If((rowhammer_state_counter - 1) == 0,
                       
                        # A timer for a pair of states (state 1 and 2 in this case)
                        # Access here means theres only one rowhammer state being used.
                        If((rowhammer_two_states_counter_sig - 1) == 0, 
                        
                            # A timer to control when to either repeat the cycle of states or 
                            # finish sending commands.
                            If((rowhammer_state_cycle_counter - 1) == 0,
                                NextState("RH_RESET_SETTINGS"),
                            ).Else(
                                NextValue(rowhammer_state_cycle_counter, rowhammer_state_cycle_counter - 1),
                                NextValue(rowhammer_state_counter, num_addrs_attack_sig),
                                NextValue(rowhammer_attack_cmd_timer_sig, addr_1_freq_sig),
                                NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_1_storage_sig),
                                NextState("RH_ATTACK_1"),
                            ),

                        ).Else(
                            NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_sig - 1),
                            NextValue(rowhammer_attack_cmd_timer_sig, addr_1_freq_sig),
                            NextState("RH_ATTACK_1"),
                        ),

                    ).Else(
                        NextValue(rowhammer_state_counter, rowhammer_state_counter - 1),
                        NextValue(rowhammer_attack_cmd_timer_sig, addr_2_freq_sig),
                        NextValue(self.address_csr.status, addr_2_val_sig),
                        NextState("RH_ATTACK_2"),
                    ),
                ).Else(
                    # Stay in this state till this freq timer finishes
                    NextValue(rowhammer_attack_cmd_timer_sig, rowhammer_attack_cmd_timer_sig - 1)   
                ),
            ),
            If(rw_test_port.cmd.ready & ~rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter + 1),   
            ).Elif(~rw_test_port.cmd.ready & rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter - 1),         
            ),
        )

        rh_fsm.act("RH_ATTACK_2",
            self.feedback_state_csr.status.eq(RH_ROWHAMMER_STATE | RH_SECOND_STATE),

            # Set command valid
            rw_test_port.cmd.valid.eq(1),

            # Control necessary signals for reads
            rw_test_port.cmd.we.eq(0),
            rw_test_port.rdata.ready.eq(1),

            # Control if we need to quit or move on to next bit after command execution
            If(rw_test_port.cmd.ready,
               
                # A timer containing the number of times to hammer the bit (addr_#_freq_sig)
                # Once it finishes, we go to a next state (RH_RESET_SETTINGS, RH_ATTACK_1, RH_ATTACK_2)
                If((rowhammer_attack_cmd_timer_sig - 1) == 0,
                   
                    # A timer controlling whether to 1. continue the cycle of states, or 
                    # 2. repeat the cycle of states (go back to the first state) or finish.
                    If((rowhammer_state_counter - 1) == 0,
                       
                        # A timer for a pair of states (state 1 and 2 in this case)
                        # Access here means theres only one rowhammer state being used.
                        If((rowhammer_two_states_counter_sig - 1) == 0, 
                    
                            # A timer to control when to either repeat the cycle of states or 
                            # finish sending commands.
                            If((rowhammer_state_cycle_counter - 1) == 0,
                                NextState("RH_RESET_SETTINGS"),
                            ).Else(
                                NextValue(rowhammer_state_cycle_counter, rowhammer_state_cycle_counter - 1),
                                NextValue(rowhammer_state_counter, num_addrs_attack_sig),
                                NextValue(rowhammer_attack_cmd_timer_sig, addr_1_freq_sig),
                                NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_1_storage_sig),
                                NextValue(self.address_csr.status, addr_1_val_sig),
                                NextState("RH_ATTACK_1")
                            ),

                        ).Else(
                            NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_sig - 1),
                            NextValue(rowhammer_state_counter, rowhammer_state_counter + 1),
                            NextValue(rowhammer_attack_cmd_timer_sig, addr_1_freq_sig),
                            NextValue(self.address_csr.status, addr_1_val_sig),
                            NextState("RH_ATTACK_1"),
                        ),

                    ).Else(

                        If((rowhammer_two_states_counter_sig - 1) == 0, 
                            NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_2_storage_sig),
                            NextValue(rowhammer_state_counter, rowhammer_state_counter - 1),
                            NextValue(rowhammer_attack_cmd_timer_sig, addr_3_freq_sig),
                            NextValue(self.address_csr.status, addr_3_val_sig),
                            NextState("RH_ATTACK_3"),
                        ).Else(
                            NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_sig - 1),
                            NextValue(rowhammer_state_counter, rowhammer_state_counter + 1),
                            NextValue(rowhammer_attack_cmd_timer_sig, addr_1_freq_sig),
                            NextValue(self.address_csr.status, addr_1_val_sig),
                            NextState("RH_ATTACK_1"),
                        )
                    ),

                ).Else(
                    NextValue(rowhammer_attack_cmd_timer_sig, rowhammer_attack_cmd_timer_sig - 1)   
                ),
            ),
            If(rw_test_port.cmd.ready & ~rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter + 1),   
            ).Elif(~rw_test_port.cmd.ready & rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter - 1),         
            ),
        )

        rh_fsm.act("RH_ATTACK_3",
            self.feedback_state_csr.status.eq(RH_ROWHAMMER_STATE | RH_THIRD_STATE),
            rw_test_port.cmd.valid.eq(1),
            rw_test_port.cmd.we.eq(0),
            rw_test_port.rdata.ready.eq(1),
            If(rw_test_port.cmd.ready,
                If((rowhammer_attack_cmd_timer_sig - 1) == 0,
                    If((rowhammer_state_counter - 1) == 0,
                        If((rowhammer_two_states_counter_sig - 1) == 0, 
                            If((rowhammer_state_cycle_counter - 1) == 0,
                                NextState("RH_RESET_SETTINGS"),
                            ).Else(
                                NextValue(rowhammer_state_cycle_counter, rowhammer_state_cycle_counter - 1),
                                NextValue(rowhammer_state_counter, num_addrs_attack_sig),
                                NextValue(rowhammer_attack_cmd_timer_sig, addr_1_freq_sig),
                                NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_1_storage_sig),
                                NextValue(self.address_csr.status, addr_1_val_sig),
                                NextState("RH_ATTACK_1")
                            ),
                        ).Else(
                            NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_sig - 1),
                            NextValue(rowhammer_attack_cmd_timer_sig, addr_3_freq_sig),
                            NextState("RH_ATTACK_3"),
                        )
                    ).Else(
                        NextValue(rowhammer_state_counter, rowhammer_state_counter - 1),
                        NextValue(rowhammer_attack_cmd_timer_sig, addr_4_freq_sig),
                        NextValue(self.address_csr.status, addr_4_val_sig),
                        NextState("RH_ATTACK_4"),
                    ),
                ).Else(
                    NextValue(rowhammer_attack_cmd_timer_sig, rowhammer_attack_cmd_timer_sig - 1)   
                ),
            ),
            If(rw_test_port.cmd.ready & ~rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter + 1),   
            ).Elif(~rw_test_port.cmd.ready & rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter - 1),         
            ),
        )

        rh_fsm.act("RH_ATTACK_4",
            self.feedback_state_csr.status.eq(RH_ROWHAMMER_STATE | RH_FOURTH_STATE),
            rw_test_port.cmd.valid.eq(1),
            rw_test_port.cmd.we.eq(0),
            rw_test_port.rdata.ready.eq(1),
            If(rw_test_port.cmd.ready,
                If((rowhammer_attack_cmd_timer_sig - 1) == 0,
                    If((rowhammer_state_counter - 1) == 0,
                        If((rowhammer_two_states_counter_sig - 1) == 0,
                            If((rowhammer_state_cycle_counter - 1) == 0,
                                NextState("RH_RESET_SETTINGS"),
                            ).Else(
                                NextValue(rowhammer_state_cycle_counter, rowhammer_state_cycle_counter - 1),
                                NextValue(rowhammer_state_counter, num_addrs_attack_sig),
                                NextValue(rowhammer_attack_cmd_timer_sig, addr_1_freq_sig),
                                NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_1_storage_sig),
                                NextValue(self.address_csr.status, addr_1_val_sig),
                                NextState("RH_ATTACK_1")
                            ),
                        ).Else(
                            NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_sig - 1),
                            NextValue(rowhammer_state_counter, rowhammer_state_counter + 1),
                            NextValue(rowhammer_attack_cmd_timer_sig, addr_3_freq_sig),
                            NextValue(self.address_csr.status, addr_3_val_sig),
                            NextState("RH_ATTACK_3")
                        )
                    ).Else(

                        If((rowhammer_two_states_counter_sig - 1) == 0,
                            NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_3_storage_sig),
                            NextValue(rowhammer_state_counter, rowhammer_state_counter - 1),
                            NextValue(rowhammer_attack_cmd_timer_sig, addr_5_freq_sig),
                            NextValue(self.address_csr.status, addr_5_val_sig),
                            NextState("RH_ATTACK_5"),
                        ).Else(
                            NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_sig - 1),
                            NextValue(rowhammer_state_counter, rowhammer_state_counter + 1),
                            NextValue(rowhammer_attack_cmd_timer_sig, addr_3_freq_sig),
                            NextValue(self.address_csr.status, addr_3_val_sig),
                            NextState("RH_ATTACK_3"),
                        ),
                    ),
                ).Else(
                    NextValue(rowhammer_attack_cmd_timer_sig, rowhammer_attack_cmd_timer_sig - 1)   
                ),
            ),
            If(rw_test_port.cmd.ready & ~rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter + 1),   
            ).Elif(~rw_test_port.cmd.ready & rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter - 1),         
            ),
        )

        rh_fsm.act("RH_ATTACK_5",
            self.feedback_state_csr.status.eq(RH_ROWHAMMER_STATE | RH_FIFTH_STATE),
            rw_test_port.cmd.valid.eq(1),
            rw_test_port.cmd.we.eq(0),
            rw_test_port.rdata.ready.eq(1),
            If(rw_test_port.cmd.ready,
                If((rowhammer_attack_cmd_timer_sig - 1) == 0,
                    If((rowhammer_state_counter - 1) == 0,
                        If((rowhammer_two_states_counter_sig - 1) == 0,
                            If((rowhammer_state_cycle_counter - 1) == 0,
                                NextState("RH_RESET_SETTINGS"),
                            ).Else(
                                NextValue(rowhammer_state_cycle_counter, rowhammer_state_cycle_counter - 1),
                                NextValue(rowhammer_state_counter, num_addrs_attack_sig),
                                NextValue(rowhammer_attack_cmd_timer_sig, addr_1_freq_sig),
                                NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_1_storage_sig),
                                NextValue(self.address_csr.status, addr_1_val_sig),
                                NextState("RH_ATTACK_1")
                            ),
                        ).Else(
                            NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_sig - 1),
                            NextValue(rowhammer_attack_cmd_timer_sig, addr_5_freq_sig),
                            NextState("RH_ATTACK_5"),
                        )
                    ).Else(
                        NextValue(rowhammer_state_counter, rowhammer_state_counter - 1),
                        NextValue(rowhammer_attack_cmd_timer_sig, addr_6_freq_sig),
                        NextValue(self.address_csr.status, addr_6_val_sig),
                        NextState("RH_ATTACK_6"),
                    ),
                ).Else(
                    NextValue(rowhammer_attack_cmd_timer_sig, rowhammer_attack_cmd_timer_sig - 1)   
                ),
            ),
            If(rw_test_port.cmd.ready & ~rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter + 1),   
            ).Elif(~rw_test_port.cmd.ready & rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter - 1),         
            ),
        )

        rh_fsm.act("RH_ATTACK_6",
            self.feedback_state_csr.status.eq(RH_ROWHAMMER_STATE | RH_SIXTH_STATE),
            rw_test_port.cmd.valid.eq(1),
            rw_test_port.cmd.we.eq(0),
            rw_test_port.rdata.ready.eq(1),
            If(rw_test_port.cmd.ready,
                If((rowhammer_attack_cmd_timer_sig - 1) == 0,
                    If((rowhammer_state_counter - 1) == 0,
                        If((rowhammer_two_states_counter_sig - 1) == 0, 
                            If((rowhammer_state_cycle_counter - 1) == 0,
                                NextState("RH_RESET_SETTINGS"),
                            ).Else(
                                NextValue(rowhammer_state_cycle_counter, rowhammer_state_cycle_counter - 1),
                                NextValue(rowhammer_state_counter, num_addrs_attack_sig),
                                NextValue(rowhammer_attack_cmd_timer_sig, addr_1_freq_sig),
                                NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_1_storage_sig),
                                NextValue(self.address_csr.status, addr_1_val_sig),
                                NextState("RH_ATTACK_1"),
                            ),
                        ).Else(
                            NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_sig - 1),
                            NextValue(rowhammer_state_counter, rowhammer_state_counter + 1),
                            NextValue(rowhammer_attack_cmd_timer_sig, addr_5_freq_sig),
                            NextValue(self.address_csr.status, addr_5_val_sig),
                            NextState("RH_ATTACK_5"),
                        ),
                    ).Else(

                        If((rowhammer_two_states_counter_sig - 1) == 0,
                            NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_4_storage_sig),
                            NextValue(rowhammer_state_counter, rowhammer_state_counter - 1),
                            NextValue(rowhammer_attack_cmd_timer_sig, addr_7_freq_sig),
                            NextValue(self.address_csr.status, addr_7_val_sig),
                            NextState("RH_ATTACK_7"),
                        ).Else(
                            NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_sig - 1),
                            NextValue(rowhammer_state_counter, rowhammer_state_counter + 1),
                            NextValue(rowhammer_attack_cmd_timer_sig, addr_5_freq_sig),
                            NextValue(self.address_csr.status, addr_5_val_sig),
                            NextState("RH_ATTACK_5"),
                        ),
                    ),
                ).Else(
                    NextValue(rowhammer_attack_cmd_timer_sig, rowhammer_attack_cmd_timer_sig - 1)   
                ),
            ),
            If(rw_test_port.cmd.ready & ~rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter + 1),   
            ).Elif(~rw_test_port.cmd.ready & rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter - 1),         
            ),
        )

        rh_fsm.act("RH_ATTACK_7",
            self.feedback_state_csr.status.eq(RH_ROWHAMMER_STATE | RH_SEVENTH_STATE),
            rw_test_port.cmd.valid.eq(1),
            rw_test_port.cmd.we.eq(0),
            rw_test_port.rdata.ready.eq(1),
            If(rw_test_port.cmd.ready,
                If((rowhammer_attack_cmd_timer_sig - 1) == 0,
                    If((rowhammer_state_counter - 1) == 0,
                       If((rowhammer_two_states_counter_sig - 1) == 0,
                            If((rowhammer_state_cycle_counter - 1) == 0,
                                NextState("RH_RESET_SETTINGS"),
                            ).Else(
                                NextValue(rowhammer_state_cycle_counter, rowhammer_state_cycle_counter - 1),
                                NextValue(rowhammer_state_counter, num_addrs_attack_sig),
                                NextValue(rowhammer_attack_cmd_timer_sig, addr_1_freq_sig),
                                NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_1_storage_sig),
                                NextValue(self.address_csr.status, addr_1_val_sig),
                                NextState("RH_ATTACK_1")
                            ),
                       ).Else(
                           NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_sig - 1),
                           NextValue(rowhammer_attack_cmd_timer_sig, addr_7_freq_sig),
                           NextState("RH_ATTACK_7"),
                       )
                    ).Else(
                        NextValue(rowhammer_state_counter, rowhammer_state_counter - 1),
                        NextValue(rowhammer_attack_cmd_timer_sig, addr_8_freq_sig),
                        NextValue(self.address_csr.status, addr_8_val_sig),
                        NextState("RH_ATTACK_8"),
                    ),
                ).Else(
                    NextValue(rowhammer_attack_cmd_timer_sig, rowhammer_attack_cmd_timer_sig - 1)   
                ),
            ),
            If(rw_test_port.cmd.ready & ~rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter + 1),   
            ).Elif(~rw_test_port.cmd.ready & rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter - 1),         
            ),
        )

        rh_fsm.act("RH_ATTACK_8",
            self.feedback_state_csr.status.eq(RH_ROWHAMMER_STATE | RH_EIGHTH_STATE),
            rw_test_port.cmd.valid.eq(1),
            rw_test_port.cmd.we.eq(0),
            rw_test_port.rdata.ready.eq(1),
            If(rw_test_port.cmd.ready,
                If((rowhammer_attack_cmd_timer_sig - 1) == 0,
                    If((rowhammer_state_counter - 1) == 0,
                        If((rowhammer_two_states_counter_sig - 1) == 0,
                            If((rowhammer_state_cycle_counter - 1) == 0,
                                NextState("RH_RESET_SETTINGS"),
                            ).Else(
                                NextValue(rowhammer_state_cycle_counter, rowhammer_state_cycle_counter - 1),
                                NextValue(rowhammer_state_counter, num_addrs_attack_sig),
                                NextValue(rowhammer_attack_cmd_timer_sig, addr_1_freq_sig),
                                NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_1_storage_sig),
                                NextValue(self.address_csr.status, addr_1_val_sig),
                                NextState("RH_ATTACK_1")
                            ),
                        ).Else(
                            NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_sig - 1),
                            NextValue(rowhammer_state_counter, rowhammer_state_counter + 1),
                            NextValue(rowhammer_attack_cmd_timer_sig, addr_7_freq_sig),
                            NextValue(self.address_csr.status, addr_7_val_sig),
                            NextState("RH_ATTACK_7"),
                        )
                    ).Else(

                        If((rowhammer_two_states_counter_sig - 1) == 0,
                            NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_5_storage_sig),
                            NextValue(rowhammer_state_counter, rowhammer_state_counter - 1),
                            NextValue(rowhammer_attack_cmd_timer_sig, addr_9_freq_sig),
                            NextValue(self.address_csr.status, addr_9_val_sig),
                            NextState("RH_ATTACK_9"),
                        ).Else(
                            NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_sig - 1),
                            NextValue(rowhammer_state_counter, rowhammer_state_counter + 1),
                            NextValue(rowhammer_attack_cmd_timer_sig, addr_7_freq_sig),
                            NextValue(self.address_csr.status, addr_7_val_sig),
                            NextState("RH_ATTACK_7")
                        ),
                    ),
                ).Else(
                    NextValue(rowhammer_attack_cmd_timer_sig, rowhammer_attack_cmd_timer_sig - 1)   
                ),
            ),
            If(rw_test_port.cmd.ready & ~rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter + 1),   
            ).Elif(~rw_test_port.cmd.ready & rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter - 1),         
            ),
        )

        rh_fsm.act("RH_ATTACK_9",
            self.feedback_state_csr.status.eq(RH_ROWHAMMER_STATE | RH_NINTH_STATE),
            rw_test_port.cmd.valid.eq(1),
            rw_test_port.cmd.we.eq(0),
            rw_test_port.rdata.ready.eq(1),
            If(rw_test_port.cmd.ready,
                If((rowhammer_attack_cmd_timer_sig - 1) == 0,
                    If((rowhammer_state_counter - 1) == 0,
                        If((rowhammer_two_states_counter_sig - 1) == 0,
                            If((rowhammer_state_cycle_counter - 1) == 0,
                                NextState("RH_RESET_SETTINGS"),
                            ).Else(
                                NextValue(rowhammer_state_cycle_counter, rowhammer_state_cycle_counter - 1),
                                NextValue(rowhammer_state_counter, num_addrs_attack_sig),
                                NextValue(rowhammer_attack_cmd_timer_sig, addr_1_freq_sig),
                                NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_1_storage_sig),
                                NextValue(self.address_csr.status, addr_1_val_sig),
                                NextState("RH_ATTACK_1")
                            ),
                        ).Else(
                            NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_sig - 1),
                            NextValue(rowhammer_attack_cmd_timer_sig, addr_9_freq_sig),
                            NextState("RH_ATTACK_9"),
                        )
                    ).Else(
                        NextValue(rowhammer_state_counter, rowhammer_state_counter - 1),
                        NextValue(rowhammer_attack_cmd_timer_sig, addr_10_freq_sig),
                        NextValue(self.address_csr.status, addr_10_val_sig),
                        NextState("RH_ATTACK_10"),
                    ),
                ).Else(
                    NextValue(rowhammer_attack_cmd_timer_sig, rowhammer_attack_cmd_timer_sig - 1)   
                ),
            ),
            If(rw_test_port.cmd.ready & ~rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter + 1),   
            ).Elif(~rw_test_port.cmd.ready & rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter - 1),         
            ),
        )
        
        rh_fsm.act("RH_ATTACK_10",
            self.feedback_state_csr.status.eq(RH_ROWHAMMER_STATE | RH_TENTH_STATE),
            rw_test_port.cmd.valid.eq(1),
            rw_test_port.cmd.we.eq(0),
            rw_test_port.rdata.ready.eq(1),
            If(rw_test_port.cmd.ready,
                If((rowhammer_attack_cmd_timer_sig - 1) == 0,
                    If((rowhammer_state_counter - 1) == 0,
                        If((rowhammer_two_states_counter_sig - 1) == 0,
                            If((rowhammer_state_cycle_counter - 1) == 0,
                                NextState("RH_RESET_SETTINGS"),
                            ).Else(
                                NextValue(rowhammer_state_cycle_counter, rowhammer_state_cycle_counter - 1),
                                NextValue(rowhammer_state_counter, num_addrs_attack_sig),
                                NextValue(rowhammer_attack_cmd_timer_sig, addr_1_freq_sig),
                                NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_1_storage_sig),
                                NextValue(self.address_csr.status, addr_1_val_sig),
                                NextState("RH_ATTACK_1")
                            ),
                        ).Else(
                            NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_sig - 1),
                            NextValue(rowhammer_state_counter, rowhammer_state_counter + 1),
                            NextValue(rowhammer_attack_cmd_timer_sig, addr_9_freq_sig),
                            NextValue(self.address_csr.status, addr_9_val_sig),
                            NextState("RH_ATTACK_9"),
                        )
                    ).Else(
                        If((rowhammer_two_states_counter_sig - 1) == 0,
                            NextValue(rowhammer_state_counter, rowhammer_state_counter - 1),
                            NextValue(self.address_csr.status, addr_11_val_sig),
                            NextState("RH_ATTACK_11"),   
                        ).Else(
                            NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_sig - 1),
                            NextValue(rowhammer_state_counter, rowhammer_state_counter + 1),
                            NextValue(rowhammer_attack_cmd_timer_sig, addr_9_freq_sig),
                            NextValue(self.address_csr.status, addr_9_val_sig),
                            NextState("RH_ATTACK_9"),
                        )
                    ),
                ).Else(
                    NextValue(rowhammer_attack_cmd_timer_sig, rowhammer_attack_cmd_timer_sig - 1)   
                ),
            ),
            If(rw_test_port.cmd.ready & ~rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter + 1),   
            ).Elif(~rw_test_port.cmd.ready & rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter - 1),         
            ),
        )

        rh_fsm.act("RH_ATTACK_11",
            self.feedback_state_csr.status.eq(RH_ROWHAMMER_STATE | RH_ELEVENTH_STATE),
            rw_test_port.cmd.valid.eq(1),
            rw_test_port.cmd.we.eq(0),
            rw_test_port.rdata.ready.eq(1),
            If(rw_test_port.cmd.ready,
                If((rowhammer_state_counter - 1) == 0,
                    If((rowhammer_state_cycle_counter - 1) == 0,
                        NextState("RH_RESET_SETTINGS"),
                    ).Else(
                        NextValue(rowhammer_state_cycle_counter, rowhammer_state_cycle_counter - 1),
                        NextValue(rowhammer_state_counter, num_addrs_attack_sig),
                        NextValue(rowhammer_attack_cmd_timer_sig, addr_1_freq_sig),
                        NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_1_storage_sig),
                        NextValue(self.address_csr.status, addr_1_val_sig),
                        NextState("RH_ATTACK_1")
                    ),
                ).Else(
                    NextValue(rowhammer_state_counter, rowhammer_state_counter - 1),
                    NextValue(self.address_csr.status, addr_12_val_sig),
                    NextState("RH_ATTACK_12"),
                ),
            ),
            If(rw_test_port.cmd.ready & ~rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter + 1),   
            ).Elif(~rw_test_port.cmd.ready & rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter - 1),         
            ),
        )

        rh_fsm.act("RH_ATTACK_12",
            self.feedback_state_csr.status.eq(RH_ROWHAMMER_STATE | RH_TWELFTH_STATE),
            rw_test_port.cmd.valid.eq(1),
            rw_test_port.cmd.we.eq(0),
            rw_test_port.rdata.ready.eq(1),
            If(rw_test_port.cmd.ready,
                If((rowhammer_state_counter - 1) == 0,
                    If((rowhammer_state_cycle_counter - 1) == 0,
                        NextState("RH_RESET_SETTINGS"),
                    ).Else(
                        NextValue(rowhammer_state_cycle_counter, rowhammer_state_cycle_counter - 1),
                        NextValue(rowhammer_state_counter, num_addrs_attack_sig),
                        NextValue(rowhammer_attack_cmd_timer_sig, addr_1_freq_sig),
                        NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_1_storage_sig),
                        NextValue(self.address_csr.status, addr_1_val_sig),
                        NextState("RH_ATTACK_1")
                    ),
                ).Else(
                    NextValue(rowhammer_state_counter, rowhammer_state_counter - 1),
                    NextValue(self.address_csr.status, addr_13_val_sig),
                    NextState("RH_ATTACK_13"),
                ),
            ),
            If(rw_test_port.cmd.ready & ~rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter + 1),   
            ).Elif(~rw_test_port.cmd.ready & rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter - 1),         
            ),
        )

        rh_fsm.act("RH_ATTACK_13",
            self.feedback_state_csr.status.eq(RH_ROWHAMMER_STATE | RH_THIRTEENTH_STATE),
            rw_test_port.cmd.valid.eq(1),
            rw_test_port.cmd.we.eq(0),
            rw_test_port.rdata.ready.eq(1),
            If(rw_test_port.cmd.ready,
                If((rowhammer_state_counter - 1) == 0,
                    If((rowhammer_state_cycle_counter - 1) == 0,
                        NextState("RH_RESET_SETTINGS"),
                    ).Else(
                        NextValue(rowhammer_state_cycle_counter, rowhammer_state_cycle_counter - 1),
                        NextValue(rowhammer_state_counter, num_addrs_attack_sig),
                        NextValue(rowhammer_attack_cmd_timer_sig, addr_1_freq_sig),
                        NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_1_storage_sig),
                        NextValue(self.address_csr.status, addr_1_val_sig),
                        NextState("RH_ATTACK_1")
                    ),
                ).Else(
                    NextValue(rowhammer_state_counter, rowhammer_state_counter - 1),
                    NextValue(self.address_csr.status, addr_14_val_sig),
                    NextState("RH_ATTACK_14"),
                ),
            ),
            If(rw_test_port.cmd.ready & ~rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter + 1),   
            ).Elif(~rw_test_port.cmd.ready & rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter - 1),         
            ),
        )

        rh_fsm.act("RH_ATTACK_14",
            self.feedback_state_csr.status.eq(RH_ROWHAMMER_STATE | RH_FOURTEENTH_STATE),
            rw_test_port.cmd.valid.eq(1),
            rw_test_port.cmd.we.eq(0),
            rw_test_port.rdata.ready.eq(1),
            If(rw_test_port.cmd.ready,
                If((rowhammer_state_counter - 1) == 0,
                    If((rowhammer_state_cycle_counter - 1) == 0,
                        NextState("RH_RESET_SETTINGS"),
                    ).Else(
                        NextValue(rowhammer_state_cycle_counter, rowhammer_state_cycle_counter - 1),
                        NextValue(rowhammer_state_counter, num_addrs_attack_sig),
                        NextValue(rowhammer_attack_cmd_timer_sig, addr_1_freq_sig),
                        NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_1_storage_sig),
                        NextValue(self.address_csr.status, addr_1_val_sig),
                        NextState("RH_ATTACK_1")
                    ),
                ).Else(
                    NextValue(rowhammer_state_counter, rowhammer_state_counter - 1),
                    NextValue(self.address_csr.status, addr_15_val_sig),
                    NextState("RH_ATTACK_15"),
                ),
            ),
            If(rw_test_port.cmd.ready & ~rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter + 1),   
            ).Elif(~rw_test_port.cmd.ready & rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter - 1),         
            ),
        )

        rh_fsm.act("RH_ATTACK_15",
            self.feedback_state_csr.status.eq(RH_ROWHAMMER_STATE | RH_FIFTEENTH_STATE),
            rw_test_port.cmd.valid.eq(1),
            rw_test_port.cmd.we.eq(0),
            rw_test_port.rdata.ready.eq(1),
            If(rw_test_port.cmd.ready,
                If((rowhammer_state_counter - 1) == 0,
                    If((rowhammer_state_cycle_counter - 1) == 0,
                        NextState("RH_RESET_SETTINGS"),
                    ).Else(
                        NextValue(rowhammer_state_cycle_counter, rowhammer_state_cycle_counter - 1),
                        NextValue(rowhammer_state_counter, num_addrs_attack_sig),
                        NextValue(rowhammer_attack_cmd_timer_sig, addr_1_freq_sig),
                        NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_1_storage_sig),
                        NextValue(self.address_csr.status, addr_1_val_sig),
                        NextState("RH_ATTACK_1")
                    ),
                ).Else(
                    NextValue(rowhammer_state_counter, rowhammer_state_counter - 1),
                    NextValue(self.address_csr.status, addr_16_val_sig),
                    NextState("RH_ATTACK_16"),
                ),
            ),
            If(rw_test_port.cmd.ready & ~rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter + 1),   
            ).Elif(~rw_test_port.cmd.ready & rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter - 1),         
            ),
        )

        rh_fsm.act("RH_ATTACK_16",
            self.feedback_state_csr.status.eq(RH_ROWHAMMER_STATE | RH_SIXTEENTH_STATE),
            rw_test_port.cmd.valid.eq(1),
            rw_test_port.cmd.we.eq(0),
            rw_test_port.rdata.ready.eq(1),
            If(rw_test_port.cmd.ready,
                If((rowhammer_state_counter - 1) == 0,
                    If((rowhammer_state_cycle_counter - 1) == 0,
                        NextState("RH_RESET_SETTINGS"),
                    ).Else(
                        NextValue(rowhammer_state_cycle_counter, rowhammer_state_cycle_counter - 1),
                        NextValue(rowhammer_state_counter, num_addrs_attack_sig),
                        NextValue(rowhammer_attack_cmd_timer_sig, addr_1_freq_sig),
                        NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_1_storage_sig),
                        NextValue(self.address_csr.status, addr_1_val_sig),
                        NextState("RH_ATTACK_1")
                    ),
                ).Else(
                    NextValue(rowhammer_state_counter, rowhammer_state_counter - 1),
                    NextValue(self.address_csr.status, addr_17_val_sig),
                    NextState("RH_ATTACK_17"),
                ),
            ),
            If(rw_test_port.cmd.ready & ~rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter + 1),   
            ).Elif(~rw_test_port.cmd.ready & rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter - 1),         
            ),
        )

        rh_fsm.act("RH_ATTACK_17",
            self.feedback_state_csr.status.eq(RH_ROWHAMMER_STATE | RH_SEVENTEENTH_STATE),
            rw_test_port.cmd.valid.eq(1),
            rw_test_port.cmd.we.eq(0),
            rw_test_port.rdata.ready.eq(1),
            If(rw_test_port.cmd.ready,
                If((rowhammer_state_counter - 1) == 0,
                    If((rowhammer_state_cycle_counter - 1) == 0,
                        NextState("RH_RESET_SETTINGS"),
                    ).Else(
                        NextValue(rowhammer_state_cycle_counter, rowhammer_state_cycle_counter - 1),
                        NextValue(rowhammer_state_counter, num_addrs_attack_sig),
                        NextValue(rowhammer_attack_cmd_timer_sig, addr_1_freq_sig),
                        NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_1_storage_sig),
                        NextValue(self.address_csr.status, addr_1_val_sig),
                        NextState("RH_ATTACK_1")
                    ),
                ).Else(
                    NextValue(rowhammer_state_counter, rowhammer_state_counter - 1),
                    NextValue(self.address_csr.status, addr_18_val_sig),
                    NextState("RH_ATTACK_18"),
                ),
            ),
            If(rw_test_port.cmd.ready & ~rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter + 1),   
            ).Elif(~rw_test_port.cmd.ready & rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter - 1),         
            ),
        )

        rh_fsm.act("RH_ATTACK_18",
            self.feedback_state_csr.status.eq(RH_ROWHAMMER_STATE | RH_EIGHTEENTH_STATE),
            rw_test_port.cmd.valid.eq(1),
            rw_test_port.cmd.we.eq(0),
            rw_test_port.rdata.ready.eq(1),
            If(rw_test_port.cmd.ready,
                If((rowhammer_state_counter - 1) == 0,
                    If((rowhammer_state_cycle_counter - 1) == 0,
                        NextState("RH_RESET_SETTINGS"),
                    ).Else(
                        NextValue(rowhammer_state_cycle_counter, rowhammer_state_cycle_counter - 1),
                        NextValue(rowhammer_state_counter, num_addrs_attack_sig),
                        NextValue(rowhammer_attack_cmd_timer_sig, addr_1_freq_sig),
                        NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_1_storage_sig),
                        NextValue(self.address_csr.status, addr_1_val_sig),
                        NextState("RH_ATTACK_1")
                    ),
                ).Else(
                    NextValue(rowhammer_state_counter, rowhammer_state_counter - 1),
                    NextValue(self.address_csr.status, addr_19_val_sig),
                    NextState("RH_ATTACK_19"),
                ),
            ),
            If(rw_test_port.cmd.ready & ~rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter + 1),   
            ).Elif(~rw_test_port.cmd.ready & rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter - 1),         
            ),
        )

        rh_fsm.act("RH_ATTACK_19",
            self.feedback_state_csr.status.eq(RH_ROWHAMMER_STATE | RH_NINETEENTH_STATE),
            rw_test_port.cmd.valid.eq(1),
            rw_test_port.cmd.we.eq(0),
            rw_test_port.rdata.ready.eq(1),
            If(rw_test_port.cmd.ready,
                If((rowhammer_state_counter - 1) == 0,
                    If((rowhammer_state_cycle_counter - 1) == 0,
                        NextState("RH_RESET_SETTINGS"),
                    ).Else(
                        NextValue(rowhammer_state_cycle_counter, rowhammer_state_cycle_counter - 1),
                        NextValue(rowhammer_state_counter, num_addrs_attack_sig),
                        NextValue(rowhammer_attack_cmd_timer_sig, addr_1_freq_sig),
                        NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_1_storage_sig),
                        NextValue(self.address_csr.status, addr_1_val_sig),
                        NextState("RH_ATTACK_1")
                    ),
                ).Else(
                    NextValue(rowhammer_state_counter, rowhammer_state_counter - 1),
                    NextValue(self.address_csr.status, addr_20_val_sig),
                    NextState("RH_ATTACK_20"),
                ),
            ),
            If(rw_test_port.cmd.ready & ~rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter + 1),   
            ).Elif(~rw_test_port.cmd.ready & rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter - 1),         
            ),
        )

        rh_fsm.act("RH_ATTACK_20",
            self.feedback_state_csr.status.eq(RH_ROWHAMMER_STATE | RH_TWENTIETH_STATE),
            rw_test_port.cmd.valid.eq(1),
            rw_test_port.cmd.we.eq(0),
            rw_test_port.rdata.ready.eq(1),
            If(rw_test_port.cmd.ready,
                If((rowhammer_state_cycle_counter - 1) == 0,
                    NextState("RH_RESET_SETTINGS"),
                ).Else(
                    NextValue(rowhammer_state_cycle_counter, rowhammer_state_cycle_counter - 1),
                    NextValue(rowhammer_state_counter, num_addrs_attack_sig),
                    NextValue(rowhammer_attack_cmd_timer_sig, addr_1_freq_sig),
                    NextValue(rowhammer_two_states_counter_sig, rowhammer_two_states_counter_1_storage_sig),
                    NextValue(self.address_csr.status, addr_1_val_sig),
                    NextState("RH_ATTACK_1")
                ),
            ),
            If(rw_test_port.cmd.ready & ~rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter + 1),   
            ).Elif(~rw_test_port.cmd.ready & rw_test_port.rdata.valid,
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter - 1),         
            ),
        )

        rh_fsm.act("RH_RESET_SETTINGS",
            self.feedback_state_csr.status.eq(RH_RESET_SETTNGS_STATE),
            If(rowhammer_port_wready_rvalid_counter == 0,
                NextValue(self.burst_cntr_sig, 0),
                NextValue(self.address_csr.status, 0),
                NextValue(self.rowhammer_err_cnt_csr.status, 0),
                NextValue(self.before_after_rh_csr.status, 1),
                If(self.refresh_enable_csr.storage,
                    NextValue(trefi, trefi_setting),
                ).Else(
                    NextValue(refresh_enable, 1),
                ),
                NextValue(auto_precharge_setting, 0),
                NextValue(input_data_double_pattern_setting, 0),
                NextValue(data_sig_timer, PORT_COLS_AND_BANKS_PER_ROW_ADDR),
                NextState("READ_CHECK_REQ"), 
            ).Elif((rw_test_port.wdata.ready | rw_test_port.rdata.valid),
                NextValue(rowhammer_port_wready_rvalid_counter, rowhammer_port_wready_rvalid_counter - 1)
            )
        )

        rh_fsm.act("RH_FINAL_CHECK",
            self.feedback_state_csr.status.eq(RH_FINAL_CHECK),
            If(rowhammer_start_sig == 0,
               NextState("RH_IDLE")
            ).Else(
                NextState("RH_FINAL_CHECK")
            )
        )


        ##########################################################
        # Read portion of the state machine, used at least twice
        ##########################################################

        # Start sending reading commands (cmd.we is LOW)
        rh_fsm.act("READ_CHECK_REQ",
            self.feedback_state_csr.status.eq(RH_READ_CHECK_STATE | RH_FIRST_STATE),
            rw_test_port.cmd.valid.eq(1),
            If(self.address_csr.status == max_address_sig,
                NextValue(self.address_csr.status, 0),  
                NextState("READ_CHECK_REC"), 
            ).Else(
                NextValue(self.address_csr.status, self.address_csr.status + 1),
                NextState("READ_CHECK_REQ_REC"),
            )
        )

        # Both receive and request commands until we have sent them all.
        # This also includes getting an error count, comparing data with
        # expected data.
        rh_fsm.act("READ_CHECK_REQ_REC",
            self.feedback_state_csr.status.eq(RH_READ_CHECK_STATE | RH_SECOND_STATE),
            rw_test_port.cmd.valid.eq(1),
            rw_test_port.rdata.ready.eq(1),
            If(rw_test_port.rdata.valid,
                NextValue(self.burst_cntr_sig, self.burst_cntr_sig + 1),
                If(self.input_data_double_pattern_setting_csr.storage & input_data_double_pattern_setting,
                    If(rw_test_port.rdata.data != data_sig_2,
                       NextValue(self.rowhammer_err_cnt_csr.status, self.rowhammer_err_cnt_csr.status + 1),
                    )
                ).Else(
                    If(rw_test_port.rdata.data != data_sig_1,
                        NextValue(self.rowhammer_err_cnt_csr.status, self.rowhammer_err_cnt_csr.status + 1),
                    )
                ),
                If((data_sig_timer - 1) == 0,
                    NextValue(input_data_double_pattern_setting, ~input_data_double_pattern_setting),
                    NextValue(data_sig_timer, PORT_COLS_AND_BANKS_PER_ROW_ADDR),
                ).Else(
                    NextValue(data_sig_timer, data_sig_timer - 1),
                ),
            ),
            If(rw_test_port.cmd.ready,
                If(self.address_csr.status == max_address_sig,
                    NextValue(self.address_csr.status, 0),
                    NextState("READ_CHECK_REC"),  
                ).Else(
                    NextValue(self.address_csr.status, self.address_csr.status + 1),
                )
            )
        )

        # Finish receiving all commands, counting all errors, going now to read the errors or finish.
        rh_fsm.act("READ_CHECK_REC",
            self.feedback_state_csr.status.eq(RH_READ_CHECK_STATE | RH_THIRD_STATE),
            rw_test_port.rdata.ready.eq(1),
            If(rw_test_port.rdata.valid,
                NextValue(self.burst_cntr_sig, self.burst_cntr_sig + 1),

                If((self.burst_cntr_sig + 1) >= (max_address_sig + 1),
                    NextState("READ_FINISH"),
                    If(self.input_data_double_pattern_setting_csr.storage & input_data_double_pattern_setting,
                        If(rw_test_port.rdata.data != data_sig_2,
                            NextValue(self.rowhammer_err_cnt_csr.status, self.rowhammer_err_cnt_csr.status + 1),
                            NextValue(self.address_csr.status, 0),
                            NextValue(input_data_double_pattern_setting, 0),
                            NextValue(data_sig_timer, PORT_COLS_AND_BANKS_PER_ROW_ADDR),
                            NextState("READ_CHECK_ERR_REQ"),
                        ).Elif(self.rowhammer_err_cnt_csr.status > 0,
                            NextValue(self.address_csr.status, 0),
                            NextValue(input_data_double_pattern_setting, 0),
                            NextValue(data_sig_timer, PORT_COLS_AND_BANKS_PER_ROW_ADDR),
                            NextState("READ_CHECK_ERR_REQ"),       
                        )
                    ).Else(
                        If(rw_test_port.rdata.data != data_sig_1,
                            NextValue(self.rowhammer_err_cnt_csr.status, self.rowhammer_err_cnt_csr.status + 1),
                            NextValue(self.address_csr.status, 0),
                            NextValue(input_data_double_pattern_setting, 0),
                            NextValue(data_sig_timer, PORT_COLS_AND_BANKS_PER_ROW_ADDR),
                            NextState("READ_CHECK_ERR_REQ"),
                        ).Elif(self.rowhammer_err_cnt_csr.status > 0,
                            NextValue(self.address_csr.status, 0),
                            NextValue(input_data_double_pattern_setting, 0),
                            NextValue(data_sig_timer, PORT_COLS_AND_BANKS_PER_ROW_ADDR),
                            NextState("READ_CHECK_ERR_REQ"),       
                        )
                    ),
                ).Else(

                    If(self.input_data_double_pattern_setting_csr.storage & input_data_double_pattern_setting,
                        If(rw_test_port.rdata.data != data_sig_2,
                            NextValue(self.rowhammer_err_cnt_csr.status, self.rowhammer_err_cnt_csr.status + 1),
                        )
                    ).Else(
                        If(rw_test_port.rdata.data != data_sig_1,
                            NextValue(self.rowhammer_err_cnt_csr.status, self.rowhammer_err_cnt_csr.status + 1),
                        )
                    ),
                    If((data_sig_timer - 1) == 0,
                        NextValue(input_data_double_pattern_setting, ~input_data_double_pattern_setting),
                        NextValue(data_sig_timer, PORT_COLS_AND_BANKS_PER_ROW_ADDR),
                    ).Else(
                        NextValue(data_sig_timer, data_sig_timer - 1),
                    ),
                )
            )
        )

        # Send one request for an error address
        rh_fsm.act("READ_CHECK_ERR_REQ",
            self.feedback_state_csr.status.eq(RH_READ_SEND_ERRORS_STATE | RH_FIRST_STATE),
            rw_test_port.cmd.valid.eq(1),
            If(rw_test_port.cmd.ready,
                NextState("READ_CHECK_ERR_REC"),
            )
        )

        # Receive the response
        rh_fsm.act("READ_CHECK_ERR_REC",
            self.feedback_state_csr.status.eq(RH_READ_SEND_ERRORS_STATE | RH_SECOND_STATE),
            rw_test_port.rdata.ready.eq(1),
            If(rw_test_port.rdata.valid,
                NextValue(error_data, rw_test_port.rdata.data),
                NextState("READ_CHECK_ERR_DISPLAY"),
            )
        )

        # Set flag high. In this state, the complete data read back 
        # should be stored in CSR registers.
        # We also have a saved error counter with all the 
        # addresses that contained errors. 
        # User sets a one-shot signal high, can set it low again 
        # to receive new data.
        rh_fsm.act("READ_CHECK_ERR_DISPLAY",
            self.feedback_state_csr.status.eq(RH_READ_SEND_ERRORS_STATE | RH_THIRD_STATE),


            If(self.input_data_double_pattern_setting_csr.storage & input_data_double_pattern_setting,
                If((error_data == data_sig_2) | error_ack_sig,
                    If((self.address_csr.status + 1) == max_address_sig,
                        NextState("READ_FINISH"),
                        NextValue(self.address_csr.status, 0),
                    ).Else(
                        NextValue(self.address_csr.status, self.address_csr.status + 1),
                        If((data_sig_timer - 1) == 0,
                            NextValue(input_data_double_pattern_setting, ~input_data_double_pattern_setting),
                            NextValue(data_sig_timer, PORT_COLS_AND_BANKS_PER_ROW_ADDR),
                        ).Else(
                            NextValue(data_sig_timer, data_sig_timer - 1),
                        ),
                        NextState("READ_CHECK_ERR_REQ"),
                    )
                ).Else(
                    self.error_found_flag_csr.status.eq(1),
                )
            ).Else(
                If((error_data == data_sig_1) | error_ack_sig,
                    If((self.address_csr.status + 1) == max_address_sig,
                        NextState("READ_FINISH"),
                        NextValue(self.address_csr.status, 0),
                    ).Else(
                        NextValue(self.address_csr.status, self.address_csr.status + 1),
                        If((data_sig_timer - 1) == 0,
                            NextValue(input_data_double_pattern_setting, ~input_data_double_pattern_setting),
                            NextValue(data_sig_timer, PORT_COLS_AND_BANKS_PER_ROW_ADDR),
                        ).Else(
                            NextValue(data_sig_timer, data_sig_timer - 1),
                        ),
                        NextState("READ_CHECK_ERR_REQ"),
                    )
                ).Else(
                    self.error_found_flag_csr.status.eq(1),
                )
            ),


            # If((error_data == data_sig) | error_ack_sig,
            #     If((self.address_csr.status + 1) == max_address_sig,
            #         NextState("READ_FINISH"),
            #         NextValue(self.address_csr.status, 0),
            #     ).Else(
            #         NextValue(self.address_csr.status, self.address_csr.status + 1),
            #         NextState("READ_CHECK_ERR_REQ"),
            #     )
            # ).Else(
            #     self.error_found_flag_csr.status.eq(1),
            # )
        )


        rh_fsm.act("READ_FINISH",
            self.feedback_state_csr.status.eq(RH_READ_CHECK_STATE | RH_FOURTH_STATE),
            NextValue(self.address_csr.status, 0),
            If(self.before_after_rh_csr.status, 
                NextState("RH_FINAL_CHECK"),
            ).Else(
                NextState("RH_INIT_SETTINGS"),
            )
        )




        """
        Row Hammer sync block
        """

        self.sync += [

            # Buffered Input
            rowhammer_start_buf1_sig.eq(self.rowhammer_start_fsm_csr.storage),
            rowhammer_start_buf2_sig.eq(rowhammer_start_buf1_sig),

            # Oneshot
            If(rowhammer_start_buf2_sig,
                # One shot code
                # If(self.rowhammer_start_prev_fsm_csr.status,
                #     rowhammer_start_sig.eq(0),
                #     self.rowhammer_start_prev_fsm_csr.status.eq(1),
                # ).Else(
                #     rowhammer_start_sig.eq(1),
                #     self.rowhammer_start_prev_fsm_csr.status.eq(1),
                # )
                rowhammer_start_sig.eq(1),
                self.rowhammer_start_prev_fsm_csr.status.eq(1),
            ).Else(
                rowhammer_start_sig.eq(0),
                self.rowhammer_start_prev_fsm_csr.status.eq(0),
            )
        ]


        """
        Error acknowledging sync block
        """

        self.sync += [

            error_ack_buf1_sig.eq(self.error_ack_csr.storage),
            error_ack_buf2_sig.eq(error_ack_buf1_sig),

            # Oneshot
            If(error_ack_buf2_sig,
                If(self.error_ack_prev_csr.status,
                    error_ack_sig.eq(0),
                    self.error_ack_prev_csr.status.eq(1)   
                ).Else(
                    error_ack_sig.eq(1),
                    self.error_ack_prev_csr.status.eq(1),
                )
            ).Else(
                error_ack_sig.eq(0),
                self.error_ack_prev_csr.status.eq(0),
            )
        ]


        """
        If we want two data patterns: 
        1. First get single data patterns writing correctly
        2. Create a way to store both data patterns systematically
        3. When we write to initialize data, set even addresses data to data_sig[0:rw_test_port.data_width], odd addresses data to data_sig[rw_test_port.data_width:rw_test_port.data_width * 2]
        4. Check data in the same way as writing it
        5. Hammer the data in the same way (this might be too tricky)
        """




        """
        Comb block
        """

        self.comb += [

            # # Set the data to write with a replicated CSR register
            # data_sig.eq(Replicate(self.input_data_pattern_csr.storage, rw_test_port.data_width // len(self.input_data_pattern_csr.storage))),
            # rw_test_port.wdata.data.eq(data_sig),

            # Set the cmd address to the current value of the address signal
            rw_test_port.cmd.addr.eq(self.address_csr.status),

            # Get the max address possible in fpga
            max_address_sig.eq(~0),

            # Set the write-enable data signal to all ones in case
            # byte-enabled writes are supported
            rw_test_port.wdata.we.eq(~0),
            
        ]

        # Set the data CSR registers to rdata.data
        for i in range(1, 19):
            if (i * WIDTH_32_BITS) <= rw_test_port.data_width:
                self.comb += getattr(self, "output_data_pattern{index}_csr".format(index = i)).status.eq(error_data[WIDTH_32_BITS * (i - 1):WIDTH_32_BITS * (i)])

            else:
                self.comb += getattr(self, "output_data_pattern{index}_csr".format(index = i)).status.eq(0)












        