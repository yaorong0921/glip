"""
Common functionality to test channel multiplexing
"""

import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge
from cocotb.result import TestFailure

_fifo_data = []
_fifo_data_2 = []
_fifo_data_3 = []

@cocotb.coroutine
def channel_demultiplexer_write(dut, clk, channel_number, max_delay, write_items):
    """
    Ingress path: write to GLIP interface

    Before writing into different channels, wait between 0 and max_delay cycles.
    """
    # Mirroring expected contents of the FIFO
    channel_count = 0    
    while (channel_count < channel_number):
        fifo_wrcnt = 0
        _fifo_data_item = []
        # insert random wait before write to the next channel
        wr_delay = random.randint(0, max_delay)
        dut._log.debug("WRITE: Wait for %d clock cycles to write into channel no. %d" % (wr_delay,channel_count))
        for _ in range(wr_delay):
            yield RisingEdge(clk)
        # make sure that the full signal is stable before checking for it
        yield FallingEdge(clk)
        # write control word
        data = int("c001",16)
        dut.fifo_in_data <= data
        dut.fifo_in_valid <= 1
        yield FallingEdge(clk)
        # write channel number
        data = int("ab"+'{:02x}'.format(channel_count),16)
        dut.fifo_in_data <= data
        dut.fifo_in_valid <=1
        # write random word
        while (fifo_wrcnt < write_items):
            data = random.getrandbits(dut.WIDTH.value.integer)
            # write control number two times if control number is sent as data
            if data == int("c001",16):
                yield FallingEdge(clk)
                dut.fifo_in_data <= data
                _fifo_data_item.append(data)
                dut.fifo_in_valid <= 1
                fifo_wrcnt += 1
                # send control word again
                yield FallingEdge(clk)
                dut.fifo_in_data <= data
                _fifo_data_item.append(data)
                dut.fifo_in_valid <= 1
                fifo_wrcnt += 1
                dut._log.debug("WRITE: Wrote word %d to FIFO, value 0x%x" % (fifo_wrcnt, data))
            else :
                yield FallingEdge(clk)
                dut.fifo_in_data <= data
                _fifo_data_item.append(data)
                dut.fifo_in_valid <= 1
                fifo_wrcnt += 1   

        _fifo_data.append(_fifo_data_item)
        channel_count += 1


@cocotb.coroutine
def channel_demultiplexer_read(dut, clk, channel_number, max_delay, read_items):
    """
    Ingress path: read from FIFO of each channel.
    """
    channel_count = 0

    while (channel_count < channel_number):
        fifo_rdcnt = 0
        # determine wait cycles before next read
        rd_delay = random.randint(0, max_delay)
        # wait until the next read operation
        if rd_delay != 0:
            # unable read if we have wait cycles
            for _ in range(rd_delay):
                yield RisingEdge(clk[channel_count])
        # wait until all signals are stable in this cycle before we check
        yield FallingEdge(clk[channel_count])
        dut.fifo_in_ready_channel[channel_count] <= 1

        while (fifo_rdcnt < read_items):
            if dut.fifo_in_valid_channel[channel_count].value != 1:
                dut._log.debug("READ: channel %d is not empty" % (channel_count))
                yield RisingEdge(clk[channel_count])
                # get current data word
                data_read = dut.fifo_in_data_channel[channel_count].value.integer
                dut._log.debug("READ: Got 0x%x in read %d" % (data_read, fifo_rdcnt))
                 # check read data word
                data_expected = _fifo_data[channel_count].pop(0)
                if data_read != data_expected:
                    raise TestFailure("READ: Expected 0x%x, got 0x%x at read %d" % (data_expected, data_read, fifo_rdcnt))
                # acknowledge read
                dut.fifo_in_ready_channel[channel_count] <= 1
                fifo_rdcnt += 1
            else:
                # raise TestFailure("READ: Channel %d is empty!" % (channel_count))
                dut._log.debug("READ: Channel %d is empty!" % (channel_count))
                break
            # done with this cycle, wait for the next one
        # unable read and reset for the current channel
        yield RisingEdge(clk[channel_count])
        dut.fifo_in_ready_channel[channel_count] <= 0

        channel_count = channel_count + 1

@cocotb.coroutine
def channel_multiplexer_write(dut, clk, channel_number, max_delay, write_items):
    """
    Egress path: write to different channel

    Before writing into different channels, wait between 0 and max_delay cycles.
    """

    channel_count = 0    
    while (channel_count < channel_number):
        fifo_wrcnt = 0
        _fifo_data_item = []
        
        # insert random wait before write to the next channel
        wr_delay = random.randint(0, max_delay)
        dut._log.debug("WRITE: Wait for %d clock cycles to write into channel no. %d" % (wr_delay,channel_count))
        for _ in range(wr_delay):
            yield RisingEdge(clk[channel_count])

        # make sure that the full signal is stable before checking for it
        yield FallingEdge(clk[channel_count])

        # write random word
        while (fifo_wrcnt < write_items):
            data = random.getrandbits(dut.WIDTH.value.integer)
            _fifo_data_item.append(data)
            dut.fifo_out_valid_channel[channel_count] <= 1
            dut.fifo_out_data_channel[channel_count] <= data

            yield FallingEdge(clk[channel_count])
            dut.fifo_out_valid_channel[channel_count] <= 0

            fifo_wrcnt += 1
            dut._log.debug("WRITE: Wrote word %d to FIFO, value 0x%x" % (fifo_wrcnt, data))

        channel_count += 1
        _fifo_data.append(_fifo_data_item)

@cocotb.coroutine
def channel_multiplexer_read(dut, clk, channel_number, max_delay, read_items):
    """
    Egress path: read from GLIP interface
    """
    fifo_rdcnt = 0
    # insert random wait before reading
    rd_delay = random.randint(0, max_delay)
    dut._log.debug("READ: Wait for %d clock cycles" % (rd_delay))
    # wait until the next read operation
    if rd_delay != 0:
        # deactivate read request if we have wait cycles
        dut.fifo_out_ready <= 0
        for _ in range(rd_delay):
            yield RisingEdge(clk)

    # wait until all signals are stable in this cycle before we check
    # its value
    yield FallingEdge(clk)
    channel_count = 0

    while((fifo_rdcnt != channel_number * read_items) or (dut.fifo_out_valid.value.integer == 1)):
        yield FallingEdge(clk)
        if dut.fifo_out_valid.value.integer:
            data_read = dut.fifo_out_data.value.integer
            dut.fifo_out_ready <= 1
            # if get a control word, to check whether changing channel or sending data
            if data_read != int('c001',16):
                data_expected = _fifo_data[channel_count].pop(0)
                dut._log.debug("data_read = 0x%x" % data_read)
                fifo_rdcnt = fifo_rdcnt + 1
                if data_read != data_expected:
                    raise TestFailure("READ: Expected 0x%x, got 0x%x at channel %d" % (data_expected, data_read, channel_count))
            else:
                dut._log.debug("data_read = 0x%x" % data_read)
                yield FallingEdge(clk)

                if dut.fifo_out_valid.value:
                    data_read = dut.fifo_out_data.value.integer
                    data_read_str = '{:04x}'.format(dut.fifo_out_data.value.integer)
                    dut._log.debug("data_read = 0x%x" % data_read)
                    # send control word as data 
                    if data_read == int('c001',16):
                        data_expected = _fifo_data[channel_count].pop(0)
                        fifo_rdcnt = fifo_rdcnt + 1
                        if data_read != data_expected:
                            raise TestFailure("READ: Expected 0x%x, got 0x%x at channel %d" % (data_expected, data_read, channel_count))
                    # channel changed
                    else:
                        channel_count = int(data_read_str[2:4],16)
                        dut._log.debug("READ: change channel to no.%d" % (channel_count))


@cocotb.coroutine
def channel_demultiplexer_write_loop(dut, clk, channel_number, write_items, loop_num):
    """
    Ingress path: write to GLIP interface
    """
    # Mirroring expected contents of the FIFO
    channel_count = 0
    loop_count = 0
    while (loop_count < loop_num):
        fifo_wrcnt = 0
        _fifo_data_item = []
        # insert wait before write to the next channel
        dut._log.debug("WRITE: Channel No. %d, round No. %d" % (channel_count, loop_count))
        dut.com_rst <= 0
        # make sure that the full signal is stable before checking for it
        yield FallingEdge(clk)
        # write control word
        data = int("c001",16)
        dut.fifo_in_data <= data
        dut.fifo_in_valid <= 1
        yield FallingEdge(clk)
        # write channel number
        data = int("ab"+'{:02x}'.format(channel_count),16)
        dut.fifo_in_data <= data
        dut.fifo_in_valid <=1

        # write random word
        while (fifo_wrcnt < write_items):
            data = random.getrandbits(dut.WIDTH.value.integer)
            if (dut.fifo_in_ready != 1):
                dut._log.debug("WRITE: channel %d is full " % (channel_count))
                break
            else: 
                # write control number two times if control number is sent as data
                if data == int("c001",16):
                    yield FallingEdge(clk)
                    dut.fifo_in_data <= data
                    dut.fifo_in_valid <= 1
                    fifo_wrcnt += 1
                    # send control word again
                    yield FallingEdge(clk)
                    dut.fifo_in_data <= data
                    dut.fifo_in_valid <= 1
                    fifo_wrcnt += 1
                    _fifo_data_2.append(data)
                    dut._log.debug("WRITE: Wrote word %d to FIFO %d, value 0x%x" % (fifo_wrcnt, channel_count, data))
                else :
                    yield FallingEdge(clk)
                    dut.fifo_in_data <= data
                    _fifo_data_2.append(data)
                    dut.fifo_in_valid <= 1
                    fifo_wrcnt += 1
                    dut._log.debug("WRITE: Wrote word %d to FIFO %d, value 0x%x" % (fifo_wrcnt, channel_count, data))  
        if fifo_wrcnt == write_items:
            yield FallingEdge(clk)
            # unable write into channel when changing channel.
            dut.fifo_in_valid <= 0;
            yield FallingEdge(clk)

        channel_count = (channel_count + 1) % channel_number
        loop_count = loop_count + 1
        if loop_count % 500 == 0:
            dut._log.info("Demultiplexer: Round No. %d" % (loop_count))

@cocotb.coroutine
def channel_demultiplexer_read_loop(dut, clk, channel_number, read_items, loop_num):
    """
    Ingress path: read from FIFO of each channel.
    """
    channel_count = 0
    loop_count = 0
    
    while (loop_count < loop_num):
        fifo_rdcnt = 0
        dut._log.debug("READ: Channel No. %d, round No. %d" % (channel_count, loop_count))

        # wait until all signals are stable in this cycle before we check
        yield FallingEdge(clk[channel_count])

        while (fifo_rdcnt < read_items):
            if dut.fifo_in_valid_channel[channel_count].value != 1:
                dut._log.debug("READ: Channel %d is not empty!" % (channel_count))
                # get current data word
                yield FallingEdge(clk[channel_count])
                data_read = dut.fifo_in_data_channel[channel_count].value.integer
                dut._log.debug("READ: Got 0x%x in read %d" % (data_read, fifo_rdcnt))
                 # check read data word
                data_expected = _fifo_data_2.pop(0)
                if data_read != data_expected:
                    raise TestFailure("READ: Expected 0x%x, got 0x%x at read %d" % (data_expected, data_read, fifo_rdcnt))
                if data_read == int("c001",16):
                    fifo_rdcnt += 1
                # acknowledge read
                dut.fifo_in_ready_channel[channel_count] <= 1
                fifo_rdcnt += 1
            else:
                # raise TestFailure("READ: Channel %d is empty!" % (channel_count))
                dut._log.debug("READ: Channel %d is empty!" % (channel_count))
                break
            # done with this cycle, wait for the next one
        yield FallingEdge(clk[channel_count])
        if fifo_rdcnt == read_items:
            loop_count += 1
        # unable read for the current channel after the fifo_in_valid is set again.
        dut.fifo_in_ready_channel[channel_count] <= 0
        yield FallingEdge(clk[channel_count])
        channel_count = (channel_count + 1) % channel_number

@cocotb.coroutine
def channel_multiplexer_write_loop(dut, clk, channel_number, max_delay, write_items, loop_num):
    """
    Egress path: write to different channel

    Before writing into different channels, wait between 0 and max_delay cycles.
    """
    loop_count = 0
    channel_count = 0
    
    while (loop_count < loop_num):
        fifo_wrcnt = 0
        # insert random wait before write to the next channel
        wr_delay = random.randint(0, max_delay)
        dut._log.debug("WRITE: Wait for %d clock cycles to write into channel no. %d" % (wr_delay,channel_count))
        for _ in range(wr_delay):
            yield RisingEdge(clk[channel_count])

        # make sure that the full signal is stable before checking for it
        yield FallingEdge(clk[channel_count])
        
        # write random word
        while (fifo_wrcnt < write_items):
            data = random.getrandbits(dut.WIDTH.value.integer)
            _fifo_data_3.append(data)
            yield FallingEdge(clk[channel_count])
            dut.fifo_out_valid_channel[channel_count] <= 1
            dut.fifo_out_data_channel[channel_count] <= data

            yield FallingEdge(clk[channel_count])
            dut.fifo_out_valid_channel[channel_count] <= 0

            fifo_wrcnt += 1
            dut._log.debug("WRITE: Wrote word %d to FIFO, value 0x%x" % (fifo_wrcnt, data))

        channel_count = (channel_count + 1) % channel_number
        loop_count += 1
        if loop_count % 500 == 0:
            dut._log.info("Multiplexer: Round No. %d" % (loop_count))

@cocotb.coroutine
def channel_multiplexer_read_loop(dut, clk, channel_number, max_delay, read_items, loop_num):
    """
    Egress path: read from GLIP interface
    """
    fifo_rdcnt = 0
    loop_count = 0
    # insert random wait before reading
    rd_delay = random.randint(0, max_delay)
    dut._log.debug("READ: Wait for %d clock cycles" % (rd_delay))
    # wait until the next read operation
    if rd_delay != 0:
        # deactivate read request if we have wait cycles
        dut.fifo_out_ready <= 0
        for _ in range(rd_delay):
            yield RisingEdge(clk)

    # wait until all signals are stable in this cycle before we check its value
    yield FallingEdge(clk)
    channel_count = 0

    while((loop_count < loop_num) or (dut.fifo_out_valid.value.integer == 1)):
        yield FallingEdge(clk)
        if dut.fifo_out_valid.value.integer:
            data_read = dut.fifo_out_data.value.integer
            dut.fifo_out_ready <= 1
            # if get a control word, to check whether changing channel or sending data
            if data_read != int('c001',16):
                data_expected = _fifo_data_3.pop(0)
                dut._log.debug("data_read = 0x%x" % data_read)
                fifo_rdcnt = fifo_rdcnt + 1
                if data_read != data_expected:
                    raise TestFailure("READ: Expected 0x%x, got 0x%x at channel %d" % (data_expected, data_read, channel_count))
            else:
                dut._log.debug("data_read = 0x%x" % data_read)
                yield FallingEdge(clk)

                if dut.fifo_out_valid.value:
                    data_read = dut.fifo_out_data.value.integer
                    data_read_str = '{:04x}'.format(dut.fifo_out_data.value.integer)
                    dut._log.debug("data_read = 0x%x" % data_read)
                    # send control word as data 
                    if data_read == int('c001',16):
                        data_expected = _fifo_data_3.pop(0)
                        fifo_rdcnt = fifo_rdcnt + 1
                        if data_read != data_expected:
                            raise TestFailure("READ: Expected 0x%x, got 0x%x at channel %d" % (data_expected, data_read, channel_count))
                    # channel changed
                    else:
                        channel_count = int(data_read_str[2:4],16)
                        dut._log.debug("READ: change channel to no.%d" % (channel_count))
        if fifo_rdcnt == read_items:
            fifo_rdcnt = 0
            loop_count += 1
