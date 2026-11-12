module top #(parameter WIDTH = 16, parameter FANOUT = 1) (
    input wire clk, input wire [WIDTH-1:0] data_in,
    output wire [WIDTH-1:0] data_out
);
    wire [WIDTH-1:0] stage;
    pipe #(.WIDTH(WIDTH)) u_first(.clk(clk), .din(data_in), .dout(stage));
    if (FANOUT) begin : g_output
        pipe #(.WIDTH(WIDTH)) u_second(.clk(clk), .din(stage), .dout(data_out));
    end
endmodule

module pipe #(parameter WIDTH = 16) (input wire clk,
    input wire [WIDTH-1:0] din, output reg [WIDTH-1:0] dout);
    always @(posedge clk) dout <= din;
endmodule
