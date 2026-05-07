#include <cstdlib>
#include <systemc>
#include <tlm>

#include "cli_parser.hh"
#include "report_handler.hh"
#include "sim_control.hh"
#include "slave_transactor.hh"
#include "stats.hh"

#include "host_ucie.h"
#include "target_ucie.h"
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

    HostUCIe host_ucie("host_ucie");
    TargetUCIe target_ucie("target_ucie");
    ConvAccel conv_accel("conv_accel");

    /*
     * Full project flow:
     *
     * gem5 ExternalSlave
     *      -> Gem5SlaveTransactor
     *      -> HostUCIe
     *      -> TargetUCIe
     *      -> ConvAccel
     */
    host_ucie.target_socket.bind(transactor.socket);
    host_ucie.initiator_socket.bind(target_ucie.target_socket);
    target_ucie.initiator_socket.bind(conv_accel.target_socket);

    transactor.sim_control.bind(sim_control);

    SC_REPORT_INFO("sc_main", "Start gem5 + UCIe + accelerator endpoint simulation");

    sc_core::sc_start();

    SC_REPORT_INFO("sc_main", "End gem5 + UCIe + accelerator endpoint simulation");

    CxxConfig::statsDump();

    return EXIT_SUCCESS;
}