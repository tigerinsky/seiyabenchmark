#ifndef PUSH_PROTOCOL_H
#define PUSH_PROTOCOL_H

#include "msg.pb.h"

namespace im {

typedef struct message_t {
    char version;
    uint64_t id;
    const char* method;
    int req_proto_size;
    const char* req_proto;
} message_t;

#pragma pack(1)
typedef struct message_header_t {
    char version; 
    int proto_size;
} message_header_t;
#pragma pack()

class Protocol {
public:
    static const char kVersion = 1;

public:
    int encode(const std::string& name,
               const std::string& content,
               std::string* buf,
               uint64_t id = 0); 

    int decode(const char* input, int size, message_t* message);

private:
    im::Msg _encode_msg;
    im::Msg _decode_msg;
    
};


}

#endif
