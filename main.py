import sys
import instTranslator
import stages
import utils

import G_MEM, G_UTL

def main():

    # Read Command Arguements
    args = sys.argv[:]
    if len(args) <= 1:
        filename = "program.asm"
    elif len(args) == 3 and args[1] == "-f":
        filename = args[2]
    else:
        print("USAGE: [-f [filename] | -s]")
        return

    # Read .asm
    program = utils.readFile(filename)
    programLength = len(program)

    # Encode and load .asm into memory
    for i in range(programLength):
        # Remove comments
        if not program[i] or program[i][0] == "#": continue
        encoded = instTranslator.encode(program[i].split("#")[0])

        # Detect errors, if none then continue loading
        if encoded not in G_UTL.ERROR:
            G_MEM.INST.append(encoded)
        else:
            print("ERROR @ '{}':".format(filename))
            print("\tLine {}: '{}'".format(i+1, program[i]))
            if encoded == G_UTL.EINST:
                print("\t\tCouldn't parse the instruction")
            elif encoded == G_UTL.EARG:
                print("\t\tCouldn't parse one or more arguments")
            elif encoded == G_UTL.EFLOW:
                print("\t\tOne or more arguments are under/overflowing")
            return

    # Print the program as loaded
    utils.printInstMem()
    print()

    # Doesn't print memory after each clock
    silent = ("-s" in sys.argv)

    # Skips clock stepping
    skipSteps = silent

    # Run simulation, will run until all pipeline stages are empty
    clkHistory = []
    clk = 0
    while clk == 0 or (G_UTL.ran["IF"][1] != 0 or G_UTL.ran["ID"][1] != 0 or G_UTL.ran["EX"][1] != 0 or G_UTL.ran["MEM"][1] != 0):
        if silent:
            print("─"*20 + " CLK #{} ".format(clk) + "─"*20)
        else:
            print("─"*38 + " CLK #{} ".format(clk) + "─"*38)

        clkHistory.append([])

        # Run all stages "in parallel"
        stages.EX_fwd()
        stages.WB()
        stages.MEM()
        stages.EX()
        stages.ID()
        stages.ID_hzd()
        stages.IF()

        # Keep only the 32 LSB from memory
        for i in range(len(G_MEM.REGS)):
            G_MEM.REGS[i] &= 0xFFFFFFFF
        for i in range(len(G_MEM.DATA)):
            G_MEM.DATA[i] &= 0xFFFFFFFF

        # Report if stage was run
        for stage in ["IF", "ID", "EX", "MEM", "WB"]:
            if G_UTL.ran[stage][1] != 0:
                idle = " (idle)" if G_UTL.wasIdle[stage] else ""
                clkHistory[clk].append((stage, G_UTL.ran[stage], G_UTL.wasIdle[stage]))
                print("> Stage {}: #{} = [{}]{}.".format(stage, G_UTL.ran[stage][0]*4,
                                                         instTranslator.decode(G_UTL.ran[stage][1]), idle))

        # Print resulting memory
        if not silent:
            print("─"*(83+len(str(clk))))
            utils.printPC()
            if G_UTL.data_hzd or G_UTL.ctrl_hzd: utils.printFwdAndHazard()
            utils.printPipelineRegs()
            utils.printRegMem()
            utils.printDataMem()
            print("─"*(83+len(str(clk))))
        clk += 1

        # Clock step prompt
        if not skipSteps:
            try:
                opt = input("| step: [ENTER] | end: [E|Q] | ").lower()
                skipSteps = (opt == "e" or opt == "q")
            except KeyboardInterrupt:
                print("\nExecution aborted.")
                exit()

    if silent:
        print()
        #  utils.printPipelineRegs()
        utils.printRegMem()
        utils.printDataMem()
    else:
        print("Empty pipeline, ending execution...")

    print()
    print("Program ran in {} clocks.".format(clk))
    print()

    utils.printHistory(clkHistory)

    return

if __name__ == "__main__":
    # To print (pipe to file) pretty borders on Windows
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="UTF-8")

    main()
