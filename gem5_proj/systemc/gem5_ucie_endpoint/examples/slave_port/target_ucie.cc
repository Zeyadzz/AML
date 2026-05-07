#include "target_ucie.h"

using namespace sc_core;
using namespace tlm;

TargetUCIe::TargetUCIe(sc_module_name name) : sc_module(name),
    target_socket("target_socket"),
    initiator_socket("initiator_socket"),
    peq(this, &TargetUCIe::peq_cb),
    reconstructed_payload(nullptr),
    reconstructed_length(0)
{
    target_socket.register_nb_transport_fw(this, &TargetUCIe::nb_transport_fw);
    initiator_socket.register_nb_transport_bw(this, &TargetUCIe::nb_transport_bw);
}

tlm_sync_enum TargetUCIe::nb_transport_fw(tlm_generic_payload& trans, tlm_phase& phase, sc_time& t) {
    peq.notify(trans, phase, t);
    return TLM_ACCEPTED;
}

tlm_sync_enum TargetUCIe::nb_transport_bw(tlm_generic_payload& trans, tlm_phase& phase, sc_time& t) {
    peq.notify(trans, phase, t);
    return TLM_ACCEPTED;
}

void TargetUCIe::peq_cb(tlm_generic_payload& trans, const tlm_phase& phase) {
    if (phase == BEGIN_REQ) { // Request from Host UCIe
        UCIeFlitExtension* ext;
        trans.get_extension(ext);
        
        if (ext) {
            // Send Ack back
            ext->is_ack = true;
            tlm_phase bw_phase = BEGIN_RESP;
            sc_time delay = SC_ZERO_TIME;
            target_socket->nb_transport_bw(trans, bw_phase, delay);

            if (!reconstructed_payload) {
                reconstructed_payload = new tlm_generic_payload();
                reconstructed_payload->set_command(trans.get_command());
                reconstructed_payload->set_address(trans.get_address());
                reconstructed_length = 0;
            }

            reconstructed_length += ext->payload_size;

            if (ext->is_tail) {
                reconstructed_payload->set_data_length(reconstructed_length);
                
                // Forward reconstructed payload to Accelerator
                tlm_phase fw_phase = BEGIN_REQ;
                sc_time fw_delay = SC_ZERO_TIME;
                initiator_socket->nb_transport_fw(*reconstructed_payload, fw_phase, fw_delay);
                
                reconstructed_payload = nullptr;
            }
        }
    } else if (phase == END_REQ || phase == BEGIN_RESP) {
        // Forward responses from Accelerator back to Host
        tlm_phase bw_phase = phase;
        sc_time delay = SC_ZERO_TIME;
        target_socket->nb_transport_bw(trans, bw_phase, delay);
    }
}