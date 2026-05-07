#include <cstdlib>
#include <systemc>
#include <tlm>

#include "cli_parser.hh"
#include "report_handler.hh"
#include "sim_control.hh"
#include "slave_transactor.hh"
#include "stats.hh"

#include "host_pcie.h"
#include "target_pcie.h"
#include "conv_accel.h"

int
sc_main(int argc, char **argv)
{
    CliParser parser;
    parser.parse(argc, argv);

    sc_core::sc_report_handler::set_handler(reportHandler);

    Gem5SystemC::Gem5SimControl sim_control("gem5",
                                            parser.getConfigFile(),
                                            parser.getSimulationEnd(),
                                            parser.getDebugFlags());

    Gem5SystemC::Gem5SlaveTransactor transactor("transactor", "transactor");

    HostPCIe host_pcie("host_pcie");
    TargetPCIe target_pcie("target_pcie");
    ConvAccel conv_accel("conv_accel");

    /*
     * Full project flow:
     *
     * gem5 ExternalSlave
     *      -> Gem5SlaveTransactor
     *      -> HostPCIe
     *      -> TargetPCIe
     *      -> ConvAccel
     */
    host_pcie.target_socket.bind(transactor.socket);
    host_pcie.initiator_socket.bind(target_pcie.target_socket);
    target_pcie.initiator_socket.bind(conv_accel.target_socket);

    transactor.sim_control.bind(sim_control);

    SC_REPORT_INFO("sc_main", "Start gem5 + PCIe + accelerator endpoint simulation");

    sc_core::sc_start();

    SC_REPORT_INFO("sc_main", "End gem5 + PCIe + accelerator endpoint simulation");

    CxxConfig::statsDump();

    return EXIT_SUCCESS;
}