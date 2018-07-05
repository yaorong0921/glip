/* Copyright (c) 2018 by the author(s)
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 *
 * =============================================================================
 *
 * A module includes two modules, i.e. channel_demultiplexer and channel_multiplexer.
 *
 *
 *
 * Author(s):
 *   Yao Rong <yao.rong@tum.de>
 */
module top_channel_multiplexing #(
   parameter WIDTH = 16,
   parameter CHANN = 8,
   parameter FIFO_DEPTH = 32,
   parameter TIMEOUT = FIFO_DEPTH
)(
   // Clock
   input    clk,
   // GLIP Control Interface
   input    com_rst,
   // GLIP FIFO Interface
   input                    fifo_in_valid,
   output                   fifo_in_ready,
   input [WIDTH-1:0]        fifo_in_data,

   output                   fifo_out_valid,
   input                    fifo_out_ready,
   output [WIDTH-1:0]       fifo_out_data,

   // Clock of each channel
   input [CHANN-1:0]        fifo_clk_channel,
   // Reset of each channel
   input [CHANN-1:0]        fifo_rst_channel,
   // GLIP FIFO Interface of each channel
   output [CHANN-1:0]              fifo_in_valid_channel,
   input  [CHANN-1:0]              fifo_in_ready_channel,
   output [CHANN-1:0][WIDTH-1:0]   fifo_in_data_channel,

   input  [CHANN-1:0]              fifo_out_valid_channel,
   output [CHANN-1:0]              fifo_out_ready_channel,
   input  [CHANN-1:0][WIDTH-1:0]   fifo_out_data_channel

);

   channel_demultiplexer
   #(.WIDTH(WIDTH),
     .CHANN(CHANN),
     .FIFO_DEPTH(FIFO_DEPTH))
   u_demutliplexer(
      .clk(clk),
      .com_rst(com_rst),
      .fifo_in_valid(fifo_in_valid),
      .fifo_in_ready(fifo_in_ready),
      .fifo_in_data(fifo_in_data),
      .fifo_rd_clk_channel(fifo_clk_channel),
      .fifo_rst_channel(fifo_rst_channel),
      .fifo_in_valid_channel(fifo_in_valid_channel), 
      .fifo_in_ready_channel(fifo_in_ready_channel),
      .fifo_in_data_channel(fifo_in_data_channel)
      );

   channel_multiplexer
   #(.WIDTH(WIDTH),
     .CHANN(CHANN),
     .FIFO_DEPTH(FIFO_DEPTH),
     .TIMEOUT(TIMEOUT))
   u_mutliplexer(
      .clk(clk),
      .com_rst(com_rst),
      .fifo_out_valid(fifo_out_valid),
      .fifo_out_ready(fifo_out_ready),
      .fifo_out_data(fifo_out_data),
      .fifo_wr_clk_channel(fifo_clk_channel),
      .fifo_rst_channel(fifo_rst_channel),
      .fifo_out_valid_channel(fifo_out_valid_channel), 
      .fifo_out_ready_channel(fifo_out_ready_channel),
      .fifo_out_data_channel(fifo_out_data_channel)
      );

endmodule
