#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <time.h>


int main()
{
    
    int funNum; 
    char yourGuess[20];
    srand(time(0));
    funNum = rand();
    
    puts("Give me your fun number");
    fgets(yourGuess,1337,stdin);
    if(funNum==1337)
    {
        puts("Congrat!!!");
        system("/usr/bin/cat /root/root.txt");
    }else{
        puts("I'm sorry =))");
    }
}