"""
Test the module top channel multiplexing. Ingress path and Egress path work simultaneously.
"""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge
from cocotb.result import TestFailure

from channel_multiplexing_common import channel_multiplexer_write_loop, channel_multiplexer_read_loop
from channel_multiplexing_common import channel_demultiplexer_write_loop, channel_demultiplexer_read_loop
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
        cocotb.fork(Clock(dut.fifo_clk_channel[i], 500).start())

    # reset
    dut._log.info("Resetting DUT")
    dut.com_rst <= 1
    dut.fifo_out_ready <= 0
    dut.fifo_in_valid <= 0
    dut.fifo_in_data <= 0
    for i in range(chann_number):
        dut.fifo_rst_channel[i] <= 1
        dut.fifo_in_ready_channel[i] <= 0
        dut.fifo_out_valid_channel[i] <= 0

    for _ in range(3):
        yield RisingEdge(dut.clk)
    dut.com_rst <= 0
    for i in range(chann_number):
        dut.fifo_rst_channel[i] <= 0

    dut._log.info("Starting test...")
    # read and write simultaneously
    write_thread_ingress = cocotb.fork(channel_demultiplexer_write_loop(dut, dut.clk, chann_number, 32, 5000))
    read_thread_ingress = cocotb.fork(channel_demultiplexer_read_loop(dut, dut.fifo_clk_channel, chann_number, 32, 5000))
    write_thread_engress = cocotb.fork(channel_multiplexer_write_loop(dut, dut.fifo_clk_channel, chann_number, 5, 32, 5000))
    read_thread_engress = cocotb.fork(channel_multiplexer_read_loop(dut, dut.clk, chann_number, 5, 32, 5000))
    yield read_thread_engress.join()
    dut._log.info("Test done")
