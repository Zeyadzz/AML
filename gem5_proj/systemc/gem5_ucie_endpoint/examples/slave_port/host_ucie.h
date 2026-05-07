#ifndef HOST_UCIE_H
#define HOST_UCIE_H

#include <systemc>
#include <tlm>
#include <tlm_utils/simple_target_socket.h>
#include <tlm_utils/simple_initiator_socket.h>
#include <tlm_utils/peq_with_cb_and_phase.h>
#include <map>
#include <queue>
#include "ucie_extensions.h"

class HostUCIe : public sc_core::sc_module {
public:
    tlm_utils::simple_target_socket<HostUCIe> target_socket;
    tlm_utils::simple_initiator_socket<HostUCIe> initiator_socket;

    SC_HAS_PROCESS(HostUCIe);
    HostUCIe(sc_core::sc_module_name name);

private:
    tlm::tlm_sync_enum nb_transport_fw(tlm::tlm_generic_payload& trans, tlm::tlm_phase& phase, sc_core::sc_time& t);
    tlm::tlm_sync_enum nb_transport_bw(tlm::tlm_generic_payload& trans, tlm::tlm_phase& phase, sc_core::sc_time& t);
    
    void peq_cb(tlm::tlm_generic_payload& trans, const tlm::tlm_phase& phase);
    void tx_process();

    tlm_utils::peq_with_cb_and_phase<HostUCIe> peq;
    
    std::queue<tlm::tlm_generic_payload*> pending_transactions;
    std::map<uint64_t, tlm::tlm_generic_payload*> retry_buffer;
    
    sc_core::sc_event tx_event;
    sc_core::sc_time tx_delay;
    uint64_t next_flit_id;
};

#endif // HOST_UCIE_H