Channel Multiplexing
--------------

The Channel Multiplexing is the interface between GLIP and multiple channels in
your logic. With the help of plain protocols, the data written into the FIFO 
(we use the dualclock FWFT FIFO) of different channels in your logic will
be transmitted in one message to host PC and the other way around. 


### Overview
The Channel Multiplexing module includes two modules: **Demultiplexer** (Ingress path)
and **Multiplexer** (Egress path).

##### Demultiplexer
This module splits the data flow from host PC into different channels and stores
them in the FIFO of each channel. All the ports from this module are named similarly 
from GLIP interface.

| Port Name     | Width | Direction | Description                            |
|---------------|:-----:|:---------:|--------------------------------------- |
| clk           | 1     | Input     | clk of GLIP Interface                  |
| com_rst       | 1     | Input     | reset of GLIP Interface                |
| fifo_in_valid | 1     | Input     | the data on `fifo_in_data` is valid  |
| fifo_in_ready | 1     | Output    | the logic is ready to receive new data |
| fifo_in_data  |FIFO_WIDTH| Input  | the data to write to logic             |
| clk_rd_clk_channel|NCHANN| Input  | read clk of each channel in logic      |
| fifo_rst_channel  |NCHANN| Input  | reset of each channel in logic         |
| fifo_in_valid_channel|NCHANN|Output| the data on `fifo_in_data_channel` is valid|
| fifo_in_ready_channel|NCHANN|Input | following module is ready to recieve data from channels|
| fifo_in_data_channel |NCHANN*FIFO_WIDTH | Output| the data got from host pc|

##### Multiplexer
This module merges the data flows from different channels FIFOs into one data flow
and transmits it to host PC through GLIP interface. All the ports from this module 
are named similarly from GLIP interface.

| Port Name     | Width | Direction | Description                            |
|---------------|:-----:|:---------:|--------------------------------------- |
| clk           | 1     | Input     | clk of GLIP Interface                  |
| com_rst       | 1     | Input     | reset of GLIP Interface                |
| fifo_out_valid| 1     | Output    | the data on `fifo_out_data` is valid |
| fifo_out_ready| 1     | Input     | the GLIP is ready to receive new data  |
| fifo_out_data |FIFO_WIDTH| Output | the data to write to host              |
| clk_wr_clk_channel|NCHANN| Input  | write clk of each channel in logic     |
| fifo_rst_channel  |NCHANN| Input  | reset of each channel in logic         |
| fifo_out_valid_channel|NCHANN|Input| the data on `fifo_out_data_channel` is valid|
| fifo_out_ready_channel|NCHANN|Output| the channels are ready to recieve data|
| fifo_out_data_channel |NCHANN*FIFO_WIDTH|Output| the data from each channel |

### Protocols
##### Ingress path
- Send `CONTROL_WORD`(`C001`) to indicate channel changing.
- Send the channel number directly after `CONTROL_WORD`, which comes after `CHANNEL_NUMBER_CONTROL` (`ab`), i.e. the rest 8 bits convey the channel number.
In this case, the maximal channel number is 256.
- Data sending to the selected channel comes after channel number control. 
- If `CONTROL_WORD` is sent as data, send it twice.

##### Egress path
We use *round robin* protocol here to make it simple and fair.

- Send `CONTROL_WORD`(`C001`) to indicate channel changing.
- Send the channel number directly after `CONTROL_WORD`, which comes after `CHANNEL_NUMBER_CONTROL` (`ab`),
i.e. the rest 8 bits convey the channel number.
In this case, the maximal channel number is 256.
- After the header, the data out of this channel is sent.
- The channel should be changed if this channel is empty or maximal sending amount (`TIMEOUT`)
is reached.
- If `CONTROL_WORD` is sent as data, send it twice.

### Parameters

| Module Name       | Parameter Name | Description                            |
| ----------------- |--------------- |--------------------------------------- |
| De- / Multiplexer | WIDTH          | the data width                         |
| De- / Multiplexer | CHANN          | the number of channels in logic        |
| De- / Multiplexer | FIFO_WIDTH     | the FIFO depth of each channel in logic|
| Multiplexer       | TIMEOUT        | maximal sending amount of one channel in one round|
