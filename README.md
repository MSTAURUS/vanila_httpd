Vanula http server for GET and HEAD request
==============

settings for starting:
~~~
--host  HOST          (defaut: localhost)
--port  PORT          (defaut: 8080)
-r      DOCUMENT_ROOT (defaut: ".")
-w      WORKERS       (defaut: 6)
-c      MAX CONNECT   (defaut: 100)
--log   LOG           (defaut: httpd.log)
~~~

Result of load testing 
======================

ab -n 50000 -c 100 -r http://localhost:8080/httptest/wikipedia_russia.html

~~~
Benchmarking localhost (be patient)
Completed 5000 requests
Completed 10000 requests
Completed 15000 requests
Completed 20000 requests
Completed 25000 requests
Completed 30000 requests
Completed 35000 requests
Completed 40000 requests
Completed 45000 requests
Completed 50000 requests
Finished 50000 requests


Server Software:        my_httpd
Server Hostname:        localhost
Server Port:            8080

Document Path:          /httptest/wikipedia_russia.html
Document Length:        954824 bytes

Concurrency Level:      100
Time taken for tests:   145.855 seconds
Complete requests:      50000
Failed requests:        0
Total transferred:      47748050000 bytes
HTML transferred:       47741200000 bytes
Requests per second:    342.81 [#/sec] (mean)
Time per request:       291.710 [ms] (mean)
Time per request:       2.917 [ms] (mean, across all concurrent requests)
Transfer rate:          319694.03 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    0   0.1      0       9
Processing:    10  291  29.7    283     520
Waiting:        9  291  29.6    283     520
Total:         13  291  29.6    283     520

Percentage of the requests served within a certain time (ms)
  50%    283
  66%    290
  75%    297
  80%    303
  90%    333
  95%    357
  98%    377
  99%    390
 100%    520 (longest request)

~~~

Web server test suite
=====================

Implement a Web server. Libraries for helping manage TCP socket connections *may* be used (if server is asynchronous [epoll](https://github.com/m13253/python-asyncore-epoll) *must* be used). Libraries that implement any part of HTTP or multiprocessing model *must not* be used.

## Requirements ##

* Respond to `GET` with status code in `{200,403,404}`
* Respond to `HEAD` with status code in `{200,404}`
* Respond to all other request methods with status code `405`
* Directory index file name `index.html`
* Respond to requests for `/<file>.html` with the contents of `DOCUMENT_ROOT/<file>.html`
* Requests for `/<directory>/` should be interpreted as requests for `DOCUMENT_ROOT/<directory>/index.html`
* Respond with the following header fields for all requests:
  * `Server`
  * `Date`
  * `Connection`
* Respond with the following additional header fields for all `200` responses to `GET` and `HEAD` requests:
  * `Content-Length`
  * `Content-Type`
* Respond with correct `Content-Type` for `.html, .css, js, jpg, .jpeg, .png, .gif, .swf`
* Respond to percent-encoding URLs
* No security vulnerabilities!
* **Bonus:** init script for daemonization with commands: start, stop, restart, status

## Testing ##

* `httptest` folder from `http-test-suite` repository should be copied into `DOCUMENT_ROOT`
* Your HTTP server should listen `localhost:80`
* `http://localhost/httptest/wikipedia_russia.html` must been shown correctly in browser
* Lowest-latency response (tested using `ab`, ApacheBench) in the following fashion: `ab -n 50000 -c 100 -r http://localhost:8080/`


