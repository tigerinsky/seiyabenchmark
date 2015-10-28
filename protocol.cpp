#include "protocol.h"
#include <arpa/inet.h>
#include "common.h"

namespace im {

int Protocol::encode(const std::string& name,
                     const std::string& content,
                     std::string* buf, 
                     uint64_t id) {
    _encode_msg.Clear();
    _encode_msg.set_mid(id);
    _encode_msg.set_name(name);
    _encode_msg.set_content(content);
    int proto_size = _encode_msg.ByteSize();
    message_header_t header;
    header.version = kVersion;
    header.proto_size = htonl(proto_size);
    int new_size = buf->size() + sizeof(message_header_t) + proto_size; 
    buf->reserve(new_size);
    buf->append((char*)(&header), sizeof(header));
    buf->resize(new_size);
    if(!_encode_msg.SerializeToArray((char*)(buf->c_str() + sizeof(header)),
                               proto_size)) {
        return 1;
    }
    return 0;
}

int Protocol::decode(const char* input, int size, message_t* message) {
    if (size < sizeof(message_header_t)) {
        return -1; 
    }
    const char* p = input;
    message_header_t* header = (message_header_t*)p;
    header->proto_size = ntohl(header->proto_size);
    LOG_INFO<< "decode: package size[" << size 
        << "] version[" << (int)header->version
        << "] proto_size[" << header->proto_size << "]";
    if (header->version != kVersion) {
        return -2; 
    }
    int total_size = sizeof(message_header_t) + header->proto_size;
    if (size < total_size) {
        return -3; 
    }
    p += sizeof(message_header_t);
    _decode_msg.Clear();
    if (!_decode_msg.ParseFromArray(p, header->proto_size)) {
        return -4;
    }
    message->version = header->version;
    message->id = _decode_msg.mid();
    message->method = _decode_msg.name().c_str();
    message->req_proto_size = _decode_msg.content().size();
    message->req_proto = _decode_msg.content().c_str();
    return total_size;
}

}
