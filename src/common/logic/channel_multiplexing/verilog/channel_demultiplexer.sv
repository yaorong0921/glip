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
 * Use one GLIP FIFO interface to split message from host (PC) into multiple channels
 * on target (FPGA).
 * The maximal channel number is 256 (The channel number should be concatenated after
 * 'ab' and in 8 bits).
 *
 * Author(s):
 *   Yao Rong <yao.rong@tum.de>
 */
module channel_demultiplexer #(
   parameter WIDTH = 16,
   parameter CHANN = 8,
   parameter FIFO_DEPTH = 32
)(
   // Clock
   input    clk,
   // GLIP Control Interface
   input    com_rst,

   // GLIP FIFO Interface.
   input                    fifo_in_valid,
   output                   fifo_in_ready,
   input [WIDTH-1:0]        fifo_in_data,

   // read clock of each channel
   input [CHANN-1:0]        fifo_rd_clk_channel,
   // reset of each channel
   input [CHANN-1:0]        fifo_rst_channel,

   // GLIP FIFO Interface of each channel
   output [CHANN-1:0]               fifo_in_valid_channel, 
   input  [CHANN-1:0]               fifo_in_ready_channel,
   output [CHANN-1:0][WIDTH-1:0]    fifo_in_data_channel
);

   // Control word and channel number (in a special word starting with 'ab')
   localparam CONTROL_WORD = 16'hc001;
   localparam CHANNEL_NUMBER_CONTROL = 8'hab; // the rest 8 bit convey the channel number

   // Storing input/output to each fifo for each channel
   logic [CHANN-1:0]    fifo_wr_en_channel;
   wire [CHANN-1:0]     fifo_full_channel;

   // Internal reset
   wire     intern_rst;
   assign   intern_rst = com_rst;

   // FSM states
   // STATE_SELECT: select one channel; STATE_WRITE: write data from host to FPGA; 
   // STATE_CONTROL_WORD: decide whether to write control word as a data, or change the channel.
   localparam STATE_IDLE = 0;
   localparam STATE_SELECT = 1;
   localparam STATE_WRITE = 2;
   localparam STATE_CONTROL_WORD = 3;

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
               .wr_clk(clk),
               .wr_rst(fifo_rst_channel[i]),
               .wr_en(fifo_wr_en_channel[i]),
               .din(fifo_in_data),

               .rd_clk(fifo_rd_clk_channel[i]),
               .rd_rst(fifo_rst_channel[i]),
               .rd_en(fifo_in_ready_channel[i]),
               .dout(fifo_in_data_channel[i]),

               .full(fifo_full_channel[i]),
               .prog_full(),
               .empty(fifo_in_valid_channel[i]),
               .prog_empty()
            );
      end
   endgenerate

   reg [2:0]   state;
   logic [2:0] nxt_state;
   // Channel which is selected
   reg [7:0]   channel_number;
   logic [7:0] nxt_channel_number;
   assign fifo_in_ready = ~fifo_full_channel[channel_number];

   // Control of the FSM.
   always @(posedge clk) begin
      if (intern_rst) begin
         state <= STATE_IDLE;
         channel_number <= 0;
      end else begin
         state <= nxt_state;
         channel_number <= nxt_channel_number;
      end
   end

   // Combinatoric part of the FSM.
   always @(*) begin
      nxt_state = state;
      nxt_channel_number = channel_number;
      fifo_wr_en_channel = {(CHANN-1){1'b0}};

      case (state)
         STATE_IDLE: begin
            if (fifo_in_valid) begin
               if (fifo_in_data == CONTROL_WORD) begin
                  nxt_state = STATE_SELECT;
               end
            end
         end

         STATE_SELECT: begin
            if (fifo_in_valid) begin
               if (fifo_in_data[15:8] == CHANNEL_NUMBER_CONTROL) begin
                  nxt_state = STATE_WRITE;
                  nxt_channel_number = fifo_in_data[7:0];
               end else if (fifo_in_data != CONTROL_WORD) begin
                  nxt_state = STATE_IDLE;
               end
            end
         end

         STATE_WRITE: begin
            if (fifo_in_valid) begin
               if (fifo_in_data == CONTROL_WORD) begin
                  nxt_state = STATE_CONTROL_WORD;
               end else begin
                  fifo_wr_en_channel[channel_number] = 1'b1;
               end
            end
         end

         STATE_CONTROL_WORD: begin
            if (fifo_in_valid) begin
               if (fifo_in_data == CONTROL_WORD) begin
                  fifo_wr_en_channel[channel_number] = 1'b1;
                  if (fifo_full_channel[channel_number] != 1) begin
                     nxt_state = STATE_WRITE;
                  end
               end else if (fifo_in_data[15:8] == CHANNEL_NUMBER_CONTROL) begin
                  nxt_state = STATE_WRITE;
                  nxt_channel_number = fifo_in_data[7:0];
               end else begin
                  nxt_state = STATE_IDLE;
               end
            end
         end
      endcase
   end

endmodule
