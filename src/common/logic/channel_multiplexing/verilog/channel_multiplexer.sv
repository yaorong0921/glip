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
 * Use one GLIP FIFO interface to transmit message from multiple channels on target 
 * (FPGA) to host (PC).
 * The maximal channel number is 256 (The channel number should be concatenated after
 * 'ab' and in 8 bits).
 *
 * Author(s):
 *   Yao Rong <yao.rong@tum.de>
 */
module channel_multiplexer #(
   parameter WIDTH = 16,
   parameter CHANN = 8,
   parameter FIFO_DEPTH = 32,
   parameter TIMEOUT = FIFO_DEPTH
)(
   // Clock
   input    clk,
   // GLIP Control Interface
   input    com_rst,

   // GLIP FIFO Interface.
   output                  fifo_out_valid,
   input                   fifo_out_ready,
   output [WIDTH-1:0]      fifo_out_data,

   // Write clock of each channel
   input [CHANN-1:0]        fifo_wr_clk_channel,
   // Reset of each channel
   input [CHANN-1:0]        fifo_rst_channel,
   
   // GLIP FIFO Interface of each channel
   input  [CHANN-1:0]              fifo_out_valid_channel,
   output [CHANN-1:0]              fifo_out_ready_channel,
   input  [CHANN-1:0][WIDTH-1:0]   fifo_out_data_channel
);

   // Control word and channel number (in a special word starting with 'ab')
   localparam CONTROL_WORD = 16'hc001;
   localparam CHANNEL_NUMBER_CONTROL = 8'hab; // the rest 8 bits convey the channel number

   // Output signals
   logic             out_valid;
   assign            fifo_out_valid = out_valid;
   logic [WIDTH-1:0] out_data;
   assign            fifo_out_data = out_data;

   // Storing input/output to each fifo for each channel
   wire [CHANN-1:0]        fifo_empty_channel;
   logic [CHANN-1:0]       fifo_rd_en_channel;

   // Counter (how many data is sent from one channel)
   reg [$clog2(TIMEOUT)-1:0]     counter;
   logic [$clog2(TIMEOUT)-1:0]   nxt_counter;

   // Data to GLIP
   wire [CHANN-1:0][WIDTH-1:0]   channel_out_data;

   // Internal reset
   wire                 intern_rst;
   assign intern_rst =  com_rst;

   // Channel which is writing
   reg [$clog2(CHANN)-1:0]   channel_number;
   logic [$clog2(CHANN)-1:0] nxt_channel_number;

   // Generate N = CHANN fifos
   generate
      genvar i;
      for (i=0; i < CHANN; i=i+1) begin: fifo
         fifo_dualclock_fwft
         #(.WIDTH(16),
           .DEPTH(FIFO_DEPTH),
           .PROG_FULL(0),
           .PROG_EMPTY(0))
         u_fifo_channel(
            .wr_clk(fifo_wr_clk_channel[i]),
            .wr_rst(fifo_rst_channel[i]),
            .wr_en(fifo_out_valid_channel[i]),
            .din(fifo_out_data_channel[i]),

            .rd_clk(clk),
            .rd_rst(fifo_rst_channel[i]),
            .rd_en(fifo_rd_en_channel[i]),
            .dout(channel_out_data[i]),

            .full(fifo_out_ready_channel[i]),
            .prog_full(),
            .empty(fifo_empty_channel[i]),
            .prog_empty()
         );
      end
   endgenerate

   // FSM states for write data to GLIP FIFO
   // STATE_SETUP: send control word to inform channel change; STATE_CHANNEL_NUMBER: send header including channel number
   // STATE_READ: read data from FPGA; STATE_CONGROL_WORD: if sending data is control word, then send it twice
   localparam STATE_SETUP = 0;
   localparam STATE_CHANNEL_NUMBER = 1;
   localparam STATE_READ = 2;
   localparam STATE_CONTROL_WORD = 3;

   reg [1:0]   state;
   logic [1:0] nxt_state;

   // Control of the FSM.
   always @(posedge clk) begin
      if (intern_rst) begin
         state <= STATE_SETUP;
         channel_number <= 0;
         counter <= {($clog2(TIMEOUT)-1){1'b0}};
      end else begin
         state <= nxt_state;
         channel_number <= nxt_channel_number;
         counter <= nxt_counter;
      end
   end

   // Combinatoric part of the FSM.
   always @(*) begin
      nxt_state = state;
      nxt_channel_number = channel_number;
      nxt_counter = counter;

      out_valid = 0;
      out_data = channel_out_data[channel_number];
      fifo_rd_en_channel = {(CHANN-1){1'b0}};

      case (state)
         STATE_SETUP: begin
            if (fifo_empty_channel[channel_number] != 1) begin
               out_data = CONTROL_WORD;
               out_valid = 1;
               if (fifo_out_ready) begin
                  nxt_state = STATE_CHANNEL_NUMBER;
               end
            end else begin
               nxt_channel_number = channel_number + 1;
               if (nxt_channel_number >= CHANN) begin
                  nxt_channel_number = 0;
               end
            end
         end

         STATE_CHANNEL_NUMBER: begin
            out_data[15:8] = 8'hab;
            out_data[7:0] = channel_number;
            out_valid = 1;
            if (fifo_out_ready) begin
               nxt_state = STATE_READ;
            end
         end

         STATE_READ: begin
            if ((fifo_empty_channel[channel_number] == 1) || (counter >= TIMEOUT)) begin
               nxt_channel_number = channel_number + 1;
               if (nxt_channel_number >= CHANN) begin
                  nxt_channel_number = 0;
               end
               nxt_state = STATE_SETUP;
               nxt_counter = {($clog2(TIMEOUT)-1){1'b0}};
            end else begin
               out_valid = 1;
               fifo_rd_en_channel[channel_number] = 1'b1;
               if (channel_out_data[channel_number] == CONTROL_WORD) begin
                  nxt_state = STATE_CONTROL_WORD;
               end else begin
                  nxt_counter = counter + 1;
               end
            end
         end

         STATE_CONTROL_WORD: begin
            out_data = CONTROL_WORD;
            out_valid = 1;
            if (fifo_out_ready) begin
               nxt_state = STATE_READ;
            end
         end
      endcase
   end
   
endmodule
