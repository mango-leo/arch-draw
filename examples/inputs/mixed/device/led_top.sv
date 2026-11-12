module led_top(input logic clk, input logic write_en,
               input logic [31:0] addr, wdata, output logic LED_OUT);
    wire led_state;
    led_register u_reg(.clk(clk), .write_en(write_en && addr == 32'h40000000),
                       .data(wdata[0]), .state(led_state));
    assign LED_OUT = led_state;
endmodule

module led_register(input logic clk, write_en, data, output logic state);
    always_ff @(posedge clk) if (write_en) state <= data;
endmodule
