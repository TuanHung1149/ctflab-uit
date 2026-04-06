#include<stdio.h>
#include<stdlib.h>
#include<string.h>
#include <pwd.h>

void setpri()
{
    char* name = "[name]";
    struct passwd* pwd;
    size_t nread = 0;

    pwd = getpwnam(name);
    if (pwd == NULL) {
        printf("Cannot find UID for name %s\n", name); 
        exit(1);
    }
    setgid(pwd->pw_gid);
    setuid(pwd->pw_uid);
}

int main(){
    setpri();
    int ret = system("/home/[name]/getinfo.sh");
    return ret;
}