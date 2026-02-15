#!/usr/bin/env ruby


require 'yaml'
require 'socket'
require 'sinatra'

class DoorManager
  def query(door, command, *args)
    cmd = [ command, *args ].join(" ")
    TCPSocket.open(door['host'], door['port']) do |s|
      s.puts(cmd)
      return s.gets.chomp
    end
  end
end

configure do
  set :bind, '0.0.0.0'
  set :environment, 'production'
  config = YAML.load_file('config.yaml')
  set :app_config, config
  set :app_mgr, DoorManager.new
  set :port, config['port']
end

get '/' do
  'Hello world'
end

get '/status' do
  res = ""
  settings.app_config['doors'].each do |door|
    status = settings.app_mgr.query(door, 'status')
    res += "#{door['name']}: #{status}\n"
  end
  res
end
