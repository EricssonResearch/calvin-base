# Calvin-3

**This is work in progress, don't expect it to work any time soon!**

That said, this is a branch that is bringing major changes to Calvin:

- Moving to Python3
- Dropping Twisted in favour of asyncio
- Moving lots of functionality into stand-alone services or tools (e.g. compiler, actor store, registry)
- New, stricter format for actor definitions (implementation remains the same)
- Temporarily disabled support for CalvinConstrained
- Temporarily disabled support for transports other than calvinip (i.e. bluetooth, fcm)

One of the consequences is that the information on the wiki is not always relevant for this branch, you will need to read the code (and commit comments) to use it.


 
## What is this?

Calvin is an application environment that lets things talk to things. It comprises of both a development framework for IoT application developers, and a runtime environment which handles the running application. Calvin is based on the fundamental idea that application development should be simple and fun. There should be no unnecessary impediments between an idea and its implementation, and an app developer should not have to worry about communication protocols or hardware specifics (but will not stop you from doing it if you want to.)

## Getting Started

Go to the [Calvin Wiki](https://github.com/EricssonResearch/calvin-base/wiki) for instructions on how to install and configure Calvin, and how to write and deploy applications.

For the really impatient, the following may work:

1. At a prompt, execute: `pip install er-calvin`
2. Start a Calvin runtime: `csruntime --host localhost --gui-mock-devices`
3. Point your browser to [`http://localhost:8000`](http://localhost:8000)

If you encounter problems have a look at the wiki. If all else fails, post an issue describing the problem.

## Contact
This is a community project that was started by a team in Ericsson Research. If you have questions or problems, [report an issue](https://github.com/EricssonResearch/calvin-base/issues) and we will get back go you as soon as we can.

## Related

Other members of the Calvin family include [calvin-constrained](https://github.com/EricssonResearch/calvin-constrained), a smaller runtime aimed at supporting devices with constrained or otherwise limited resources available. 

## Open issues

Fewer than before.
