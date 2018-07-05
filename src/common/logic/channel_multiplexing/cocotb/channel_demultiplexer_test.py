"""
Test the module channel demutliplexer. Namely the ingress path: from host (PC) to target (FPGA)

The dual clock first-word-fall-through FIFO is used
"""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge
from cocotb.result import TestFailure

from channel_multiplexing_common import channel_demultiplexer_write, channel_demultiplexer_read
from channel_multiplexing_common import channel_demultiplexer_write_loop, channel_demultiplexer_read_loop

@cocotb.test()
def channel_demultiplexer_test(dut):
    """
    Test the ingress path. Write to each channel, and then check from the fifo of each channel.
    """
    # read the parameters back from the DUT to set up our model
    width = dut.WIDTH.value.integer
    chann_number = dut.CHANN.value.integer
    dut._log.info("%d bit wide FIFO with %d channels." % (width, chann_number))
    # setup write clock
    cocotb.fork(Clock(dut.clk, 500).start())
    # setup read clock for each channel 
    for i in range(chann_number):
        cocotb.fork(Clock(dut.fifo_rd_clk_channel[i], 500).start())
    # reset
    dut._log.info("Resetting DUT")
    dut.com_rst <= 1
    dut.fifo_in_valid <= 0
    dut.fifo_in_data <= 0
    for i in range(chann_number):
        dut.fifo_in_ready_channel[i] <= 0
        dut.fifo_rst_channel[i] <= 1
    for _ in range(3):
        yield RisingEdge(dut.clk)
    dut.com_rst <= 0
    for i in range(chann_number):
        dut.fifo_rst_channel[i] <= 0

    # test:
    dut._log.info("Starting first test...")
    # start write processes
    write_thread = cocotb.fork(channel_demultiplexer_write(dut, dut.clk, chann_number, 5, 32))
    yield write_thread.join()
    # start read processes
    read_thread = cocotb.fork(channel_demultiplexer_read(dut, dut.fifo_rd_clk_channel, chann_number, 5, 32))
    yield read_thread.join()
    dut._log.info("First Test done")
 
     # reset again before the second test start
    dut._log.info("Resetting DUT")
    dut.com_rst <= 1
    dut.fifo_in_valid <= 0
    dut.fifo_in_data <= 0
    for i in range(chann_number):
        dut.fifo_in_ready_channel[i] <= 0
        dut.fifo_rst_channel[i] <= 1
    for _ in range(3):
        yield RisingEdge(dut.clk)
    dut.com_rst <= 0
    for i in range(chann_number):
        dut.fifo_rst_channel[i] <= 0
    # second test: read and write simultaneously
    dut._log.info("Starting second test...")
    # start read and write processes
    write_thread = cocotb.fork(channel_demultiplexer_write_loop(dut, dut.clk, chann_number, 32, 5000))
    read_thread = cocotb.fork(channel_demultiplexer_read_loop(dut, dut.fifo_rd_clk_channel, chann_number, 32, 5000))
    # wait for read/write to finish. Read only finishes if all required data
    yield read_thread.join()
    dut._log.info("All tests done")
