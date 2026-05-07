#include "host_ucie.h"
#include <iostream>

using namespace sc_core;
using namespace tlm;

HostUCIe::HostUCIe(sc_module_name name) : sc_module(name),
    target_socket("target_socket"),
    initiator_socket("initiator_socket"),
    peq(this, &HostUCIe::peq_cb),
    tx_delay(10, SC_NS),
    next_flit_id(1)
{
    target_socket.register_nb_transport_fw(this, &HostUCIe::nb_transport_fw);
    initiator_socket.register_nb_transport_bw(this, &HostUCIe::nb_transport_bw);
    
    SC_METHOD(tx_process);
    sensitive << tx_event;
    dont_initialize();
}

tlm_sync_enum HostUCIe::nb_transport_fw(tlm_generic_payload& trans, tlm_phase& phase, sc_time& t) {
    peq.notify(trans, phase, t);
    return TLM_ACCEPTED;
}

tlm_sync_enum HostUCIe::nb_transport_bw(tlm_generic_payload& trans, tlm_phase& phase, sc_time& t) {
    peq.notify(trans, phase, t);
    return TLM_ACCEPTED;
}

void HostUCIe::peq_cb(tlm_generic_payload& trans, const tlm_phase& phase) {
    if (phase == BEGIN_REQ) { // Reqeust from Bridge
        // Accept payload and queue it
        trans.acquire();
        pending_transactions.push(&trans);
        tx_event.notify();
    } else if (phase == END_REQ || phase == BEGIN_RESP) {
        // Handle responses from Target UCIe (Acks/Naks)
        UCIeFlitExtension* ext;
        trans.get_extension(ext);
        if (ext) {
            if (ext->is_ack) {
                retry_buffer.erase(ext->flit_id);
            } else if (ext->is_nak) {
                // Retry logic would go here
            }
        }
        
        if (phase == BEGIN_RESP) {
            tlm_phase fw_phase = END_RESP;
            sc_time delay = SC_ZERO_TIME;
            initiator_socket->nb_transport_fw(trans, fw_phase, delay);
        }
    }
}

void HostUCIe::tx_process() {
    if (pending_transactions.empty()) return;

    tlm_generic_payload* trans = pending_transactions.front();
    pending_transactions.pop();

    unsigned int data_length = trans->get_data_length();
    unsigned int flit_size = 256;
    unsigned int num_flits = (data_length + flit_size - 1) / flit_size;

    for (unsigned int i = 0; i < num_flits; ++i) {
        tlm_generic_payload* flit = new tlm_generic_payload();
        flit->set_command(trans->get_command());
        flit->set_address(trans->get_address());
        
        unsigned int current_flit_size = (i == num_flits - 1) ? (data_length - i * flit_size) : flit_size;
        flit->set_data_length(current_flit_size);
        
        UCIeFlitExtension* ext = new UCIeFlitExtension();
        ext->flit_id = next_flit_id++;
        ext->payload_size = current_flit_size;
        ext->is_tail = (i == num_flits - 1);
        flit->set_extension(ext);

        retry_buffer[ext->flit_id] = flit;

        tlm_phase phase = BEGIN_REQ;
        sc_time delay = tx_delay;
        initiator_socket->nb_transport_fw(*flit, phase, delay);
    }
    
    // Notify Bridge that request was accepted
    tlm_phase phase = END_REQ;
    sc_time delay = SC_ZERO_TIME;
    target_socket->nb_transport_bw(*trans, phase, delay);
}