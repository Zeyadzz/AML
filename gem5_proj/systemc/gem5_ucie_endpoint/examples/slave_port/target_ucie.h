#ifndef TARGET_UCIE_H
#define TARGET_UCIE_H

#include <systemc>
#include <tlm>
#include <tlm_utils/simple_target_socket.h>
#include <tlm_utils/simple_initiator_socket.h>
#include <tlm_utils/peq_with_cb_and_phase.h>
#include "ucie_extensions.h"

class TargetUCIe : public sc_core::sc_module {
public:
    tlm_utils::simple_target_socket<TargetUCIe> target_socket;
    tlm_utils::simple_initiator_socket<TargetUCIe> initiator_socket;

    SC_HAS_PROCESS(TargetUCIe);
    TargetUCIe(sc_core::sc_module_name name);

private:
    tlm::tlm_sync_enum nb_transport_fw(tlm::tlm_generic_payload& trans, tlm::tlm_phase& phase, sc_core::sc_time& t);
    tlm::tlm_sync_enum nb_transport_bw(tlm::tlm_generic_payload& trans, tlm::tlm_phase& phase, sc_core::sc_time& t);
    
    void peq_cb(tlm::tlm_generic_payload& trans, const tlm::tlm_phase& phase);

    tlm_utils::peq_with_cb_and_phase<TargetUCIe> peq;
    
    tlm::tlm_generic_payload* reconstructed_payload;
    unsigned int reconstructed_length;
};

#endif // TARGET_UCIE_H