#!/usr/bin/env ruby

require 'yaml'
require 'socket'
require 'sinatra'


class DoorManager
  def initialize(door)
    @door = door
    @socket = TCPSocket.open(door['host'], door['port'])
  end

  def query(command, *args)
    cmd = [ command, *args ].join(" ")
    @socket.puts(cmd)
    return @socket.gets.chomp
  end

  def multiline_query(command, *args)
    lines = query(command, *args).chomp.to_i
    return (1..lines).map { |i| @socket.gets.chomp }
  end

  def close
    @socket.close
  end

  def self.open(door)
    dm = self.new(door)
    return dm unless block_given?
    begin
      return yield(dm)
    ensure
      dm.close
    end
  end
end

configure do
  set :bind, '0.0.0.0'
  set :environment, 'production'
  config = YAML.load_file('config.yaml')
  set :app_config, config
  set :port, config['port']
end

get '/' do
  haml <<~EOF
    !!!
    %html
      %head
        %title Door Lock Manager
      %body
        %h1 Door Lock Manager
        %ul
          %li
            %a{ :href => '/status' } Lock status
  EOF
end

get '/status' do
  res = {}
  settings.app_config['doors'].each do |door|
    begin
      res[door['name']] = DoorManager.open(door) { |dm| dm.query('status') }
    rescue
      res[door['name']] = "Error: #$!"
    end
  end
  haml <<~EOF, locals: { res: res }
    !!!
    %html
      %head
        %title Door Lock Status
      %body
        %h1 Door Lock Status
        %ul
          - res.each do |name, status|
            %li
              & \#{name}:
              %b&= status
        %p
          %i
            %a{ href: '/' } Back to home
  EOF
end
