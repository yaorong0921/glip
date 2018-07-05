"""
Test the module channel multiplexer. Namely the egress path: from target (FPGA) to host (PC)

The dual clock first-word-fall-through FIFO is used
"""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge
from cocotb.result import TestFailure

from channel_multiplexing_common import channel_multiplexer_write, channel_multiplexer_read
from channel_multiplexing_common import channel_multiplexer_write_loop, channel_multiplexer_read_loop
@cocotb.test()
def channel_multiplexer_test(dut):
    """
    Test the egress path. Write to each channel, and then check from the GLIP interface.
    """
    # read the parameters back from the DUT to set up our model
    width = dut.WIDTH.value.integer
    chann_number = dut.CHANN.value.integer
    dut._log.info("%d bit wide FIFO with %d channels." % (width, chann_number))

    # setup write clock
    cocotb.fork(Clock(dut.clk, 500).start())
    # setup read clock for each channel 
    for i in range(chann_number):
        cocotb.fork(Clock(dut.fifo_wr_clk_channel[i], 500).start())

    # reset
    dut._log.info("Resetting DUT")
    dut.com_rst <= 1
    dut.fifo_out_ready <= 0
    for i in range(chann_number):
        dut.fifo_rst_channel[i] <= 1
        dut.fifo_out_valid_channel[i] <= 0

    for _ in range(2):
        yield RisingEdge(dut.clk)
    dut.com_rst <= 0
    for i in range(chann_number):
        dut.fifo_rst_channel[i] <= 0

    # first test:
    dut._log.info("Starting first test...")
    # start write processes
    write_thread = cocotb.fork(channel_multiplexer_write(dut, dut.fifo_wr_clk_channel, chann_number, 5, 32))
    yield write_thread.join()
    # start read processes
    read_thread = cocotb.fork(channel_multiplexer_read(dut, dut.clk, chann_number, 5, 32))
    yield read_thread.join()
    dut._log.info("First test done")

    # reset again
    dut._log.info("Resetting DUT")
    dut.com_rst <= 1
    dut.fifo_out_ready <= 0
    for i in range(chann_number):
        dut.fifo_rst_channel[i] <= 1
        dut.fifo_out_valid_channel[i] <= 0

    for _ in range(2):
        yield RisingEdge(dut.clk)
    dut.com_rst <= 0
    for i in range(chann_number):
        dut.fifo_rst_channel[i] <= 0
    # second test: read and write simultaneously
    dut._log.info("Starting second test...")
    write_thread = cocotb.fork(channel_multiplexer_write_loop(dut, dut.fifo_wr_clk_channel, chann_number, 5, 32, 5000))
    read_thread = cocotb.fork(channel_multiplexer_read_loop(dut, dut.clk, chann_number, 5, 32, 5000))
    yield read_thread.join()
    dut._log.info("Second test done")
